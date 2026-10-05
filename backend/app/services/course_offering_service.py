"""Transactional course offering, assignment and enrollment operations."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterable, Sequence

from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.exceptions import (
    DomainException,
    ForbiddenException,
    NotFoundException,
    ResourceConflictException,
)
from app.models.academic import (
    ACTIVE_ENROLLMENT_STATUSES,
    Course,
    CourseEnrollment,
    CourseOffering,
    CourseOfferingTeacher,
    EnrollmentStatus,
    OfferingPublicationStatus,
    Semester,
    TeacherAssignmentRequest,
    TeacherAssignmentRequestStatus,
)
from app.models.notification import NotificationBatch
from app.models.user import User, UserRole
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


COURSE_NOTIFICATION_NAMESPACE = uuid.UUID("0d7d0f0d-6b5d-46ea-a80d-0e4eeccf7e54")
COURSE_ASSIGNMENT_NOTIFICATION = "course_assignment"
COURSE_ENROLLMENT_NOTIFICATION = "course_enrollment"


def assignment_approval_event_id(request_id: uuid.UUID) -> uuid.UUID:
    """Stable event identity shared by all recipients of one approval."""
    return uuid.uuid5(COURSE_NOTIFICATION_NAMESPACE, f"assignment-approved:{request_id}")


def enrollment_event_id(enrollment: CourseEnrollment) -> uuid.UUID:
    """Stable identity for one persisted enrollment/reselection transition."""
    updated_at = enrollment.updated_at.isoformat() if enrollment.updated_at else "pending"
    return uuid.uuid5(
        COURSE_NOTIFICATION_NAMESPACE,
        f"enrollment:{enrollment.id}:{enrollment.status}:{updated_at}",
    )


class CourseOfferingService:
    """Keep offering and enrollment rules out of AuthService and routes.

    Mutation methods commit by default for normal API calls. Registration uses
    ``enroll_many(..., commit=False)`` so account creation and initial course
    selections share AuthService's single transaction.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._pending_notification_batches: set[uuid.UUID] = set()

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    async def _finish(self, commit: bool) -> None:
        await self.db.flush()
        if commit:
            await self.db.commit()

    async def _enqueue_for_users(
        self,
        user_ids: Sequence[uuid.UUID],
        event_id: uuid.UUID,
        type_: str,
    ) -> None:
        """Enqueue generic, preference-aware notifications in the caller transaction."""
        service = NotificationService(self.db)
        for user_id in dict.fromkeys(user_ids):
            result = await service.enqueue(user_id, event_id, type_, "high")
            if result and result[1]:
                batch = await self.db.get(NotificationBatch, result[1])
                if batch is not None and batch.status == "pending":
                    self._pending_notification_batches.add(result[1])

    def publish_pending_notifications(self) -> None:
        """Publish committed push batches; the outbox recovers broker failures."""
        batch_ids = tuple(self._pending_notification_batches)
        self._pending_notification_batches.clear()
        if not batch_ids:
            return
        # Import lazily: the task module imports NotificationService itself.
        try:
            from app.tasks.notifications import deliver_notification
        except Exception:
            logger.warning("Could not load course notification publisher; outbox will recover it.")
            return

        for batch_id in batch_ids:
            try:
                deliver_notification.delay(str(batch_id))
            except Exception:
                # The DB commit is authoritative. Beat's recovery task will
                # republish a still-pending batch when Redis is unavailable.
                logger.warning("Could not publish course notification batch; outbox will recover it.")

    async def _active_students_and_crs(self) -> list[uuid.UUID]:
        return list((await self.db.scalars(
            select(User.id).where(
                User.is_active.is_(True),
                User.role.in_([UserRole.STUDENT, UserRole.CR]),
            )
        )).all())

    async def _active_assigned_teachers(self, offering_id: uuid.UUID) -> list[uuid.UUID]:
        request = aliased(TeacherAssignmentRequest)
        return list((await self.db.scalars(
            select(User.id)
            .join(CourseOfferingTeacher, CourseOfferingTeacher.teacher_id == User.id)
            .outerjoin(
                request,
                and_(
                    request.course_offering_id == CourseOfferingTeacher.course_offering_id,
                    request.teacher_id == CourseOfferingTeacher.teacher_id,
                ),
            )
            .where(
                CourseOfferingTeacher.course_offering_id == offering_id,
                User.is_active.is_(True),
                User.role == UserRole.TEACHER,
                or_(
                    request.id.is_(None),
                    request.status == TeacherAssignmentRequestStatus.APPROVED.value,
                ),
            )
        )).all())

    async def _notify_assignment_approval(self, request_id: uuid.UUID) -> None:
        await self._enqueue_for_users(
            await self._active_students_and_crs(),
            assignment_approval_event_id(request_id),
            COURSE_ASSIGNMENT_NOTIFICATION,
        )

    async def _notify_enrollment(self, enrollment: CourseEnrollment) -> None:
        if enrollment.status not in ACTIVE_ENROLLMENT_STATUSES:
            return
        recipients = [enrollment.student_id]
        recipients.extend(await self._active_assigned_teachers(enrollment.course_offering_id))
        await self._enqueue_for_users(
            recipients,
            enrollment_event_id(enrollment),
            COURSE_ENROLLMENT_NOTIFICATION,
        )

    async def _run_mutation(self, operation, *, commit: bool, conflict_message: str):
        try:
            result = await operation()
            await self._finish(commit)
            if commit:
                self.publish_pending_notifications()
            return result
        except IntegrityError as exc:
            if commit:
                await self.db.rollback()
            raise ResourceConflictException(conflict_message) from exc
        except Exception:
            if commit:
                await self.db.rollback()
            raise

    async def _offering_for_update(self, offering_id: uuid.UUID) -> CourseOffering:
        offering = await self.db.scalar(
            select(CourseOffering)
            .where(CourseOffering.id == offering_id)
            .with_for_update()
        )
        if not offering:
            raise NotFoundException("Course offering not found.")
        return offering

    async def _course(self, course_id: uuid.UUID) -> Course:
        course = await self.db.get(Course, course_id)
        if not course:
            raise NotFoundException("Course not found.")
        return course

    async def _semester(self, semester_id: int) -> Semester:
        semester = await self.db.get(Semester, semester_id)
        if not semester:
            raise NotFoundException("Semester not found.")
        return semester

    @staticmethod
    def _offering_payload(
        offering: CourseOffering,
        course: Course,
        semester: Semester,
        request_status: str | None = None,
    ) -> dict:
        return {
            "id": offering.id,
            "course_id": offering.course_id,
            "semester_id": offering.semester_id,
            "course_code": course.course_code,
            "course_title": course.title,
            # This is deliberately read from Course, never from request data.
            "credit_hours": float(course.credit_hours),
            "course_type": course.type,
            "semester_title": semester.title,
            "publication_status": offering.publication_status,
            "created_by": offering.created_by,
            "published_by": offering.published_by,
            "published_at": offering.published_at,
            "request_status": request_status,
        }

    async def _offering_details(self, offering_id: uuid.UUID) -> dict:
        row = (
            await self.db.execute(
                select(CourseOffering, Course, Semester)
                .join(Course, Course.id == CourseOffering.course_id)
                .join(Semester, Semester.id == CourseOffering.semester_id)
                .where(CourseOffering.id == offering_id)
            )
        ).one_or_none()
        if not row:
            raise NotFoundException("Course offering not found.")
        offering, course, semester = row
        return self._offering_payload(offering, course, semester)

    async def create_offering(
        self,
        admin_id: uuid.UUID,
        course_id: uuid.UUID,
        semester_id: int,
    ) -> dict:
        async def operation():
            course = await self._course(course_id)
            semester = await self._semester(semester_id)
            offering = CourseOffering(
                course_id=course.id,
                semester_id=semester.id,
                created_by=admin_id,
                publication_status=OfferingPublicationStatus.DRAFT.value,
            )
            self.db.add(offering)
            await self.db.flush()
            return self._offering_payload(offering, course, semester)

        return await self._run_mutation(
            operation,
            commit=True,
            conflict_message="An offering for this course and semester already exists.",
        )

    async def update_offering(
        self,
        offering_id: uuid.UUID,
        course_id: uuid.UUID | None = None,
        semester_id: int | None = None,
    ) -> dict:
        async def operation():
            offering = await self._offering_for_update(offering_id)
            course = await self._course(course_id or offering.course_id)
            semester = await self._semester(semester_id or offering.semester_id)
            offering.course_id = course.id
            offering.semester_id = semester.id
            offering.updated_at = self._now()
            await self.db.flush()
            return self._offering_payload(offering, course, semester)

        return await self._run_mutation(
            operation,
            commit=True,
            conflict_message="An offering for this course and semester already exists.",
        )

    async def set_publication(
        self,
        offering_id: uuid.UUID,
        admin_id: uuid.UUID,
        published: bool,
    ) -> dict:
        async def operation():
            offering = await self._offering_for_update(offering_id)
            offering.publication_status = (
                OfferingPublicationStatus.PUBLISHED.value if published else OfferingPublicationStatus.DRAFT.value
            )
            offering.published_by = admin_id if published else None
            offering.published_at = self._now() if published else None
            offering.updated_at = self._now()
            return await self._offering_details(offering.id)

        return await self._run_mutation(
            operation,
            commit=True,
            conflict_message="Could not update offering publication status.",
        )

    async def list_published_offerings(self) -> list[dict]:
        rows = (
            await self.db.execute(
                select(CourseOffering, Course, Semester)
                .join(Course, Course.id == CourseOffering.course_id)
                .join(Semester, Semester.id == CourseOffering.semester_id)
                .where(
                    CourseOffering.publication_status == OfferingPublicationStatus.PUBLISHED.value,
                    Semester.is_active.is_(True),
                )
                .order_by(Course.course_code)
            )
        ).all()
        return [self._offering_payload(offering, course, semester) for offering, course, semester in rows]

    async def list_available_offerings(self, teacher_id: uuid.UUID) -> list[dict]:
        request = aliased(TeacherAssignmentRequest)
        rows = (
            await self.db.execute(
                select(CourseOffering, Course, Semester, request.status)
                .join(Course, Course.id == CourseOffering.course_id)
                .join(Semester, Semester.id == CourseOffering.semester_id)
                .outerjoin(
                    request,
                    and_(
                        request.course_offering_id == CourseOffering.id,
                        request.teacher_id == teacher_id,
                    ),
                )
                .order_by(Semester.start_date.desc(), Course.course_code)
            )
        ).all()
        return [
            self._offering_payload(offering, course, semester, request_status)
            for offering, course, semester, request_status in rows
        ]

    async def request_assignment(self, offering_id: uuid.UUID, teacher_id: uuid.UUID) -> dict:
        async def operation():
            await self._offering_for_update(offering_id)
            teacher = await self.db.get(User, teacher_id)
            if not teacher or teacher.role != UserRole.TEACHER:
                raise ForbiddenException("Teacher role required.")
            existing = await self.db.scalar(
                select(TeacherAssignmentRequest)
                .where(
                    TeacherAssignmentRequest.course_offering_id == offering_id,
                    TeacherAssignmentRequest.teacher_id == teacher_id,
                )
                .with_for_update()
            )
            if existing:
                raise ResourceConflictException("You already requested this course offering.")
            assigned = await self.db.scalar(
                select(CourseOfferingTeacher).where(
                    CourseOfferingTeacher.course_offering_id == offering_id,
                    CourseOfferingTeacher.teacher_id == teacher_id,
                )
            )
            if assigned:
                raise ResourceConflictException("You are already assigned to this course offering.")
            request = TeacherAssignmentRequest(
                course_offering_id=offering_id,
                teacher_id=teacher_id,
                status=TeacherAssignmentRequestStatus.PENDING.value,
            )
            self.db.add(request)
            await self.db.flush()
            return request

        request = await self._run_mutation(
            operation,
            commit=True,
            conflict_message="You already requested this course offering.",
        )
        return await self._assignment_request_detail(request.id)

    async def _assignment_request_rows(self, teacher_id: uuid.UUID | None = None, status: str | None = None):
        stmt = (
            select(TeacherAssignmentRequest, CourseOffering, Course, Semester, User)
            .join(CourseOffering, CourseOffering.id == TeacherAssignmentRequest.course_offering_id)
            .join(Course, Course.id == CourseOffering.course_id)
            .join(Semester, Semester.id == CourseOffering.semester_id)
            .join(User, User.id == TeacherAssignmentRequest.teacher_id)
            .order_by(TeacherAssignmentRequest.created_at.desc())
        )
        if teacher_id is not None:
            stmt = stmt.where(TeacherAssignmentRequest.teacher_id == teacher_id)
        if status is not None:
            stmt = stmt.where(TeacherAssignmentRequest.status == status)
        return (await self.db.execute(stmt)).all()

    @staticmethod
    def _assignment_payload(request, offering, course, semester, teacher) -> dict:
        return {
            "id": request.id,
            "course_offering_id": request.course_offering_id,
            "teacher_id": request.teacher_id,
            "teacher_name": teacher.full_name,
            "course_code": course.course_code,
            "course_title": course.title,
            "semester_id": semester.id,
            "semester_title": semester.title,
            "status": request.status,
            "decided_by": request.decided_by,
            "decided_at": request.decided_at,
            "rejection_reason": request.rejection_reason,
            "created_at": request.created_at,
            "updated_at": request.updated_at,
        }

    async def list_assignment_requests(
        self,
        *,
        teacher_id: uuid.UUID | None = None,
        status: str | None = None,
    ) -> list[dict]:
        rows = await self._assignment_request_rows(teacher_id=teacher_id, status=status)
        return [self._assignment_payload(*row) for row in rows]

    async def _assignment_request_detail(self, request_id: uuid.UUID) -> dict:
        rows = await self._assignment_request_rows()
        for row in rows:
            if row[0].id == request_id:
                return self._assignment_payload(*row)
        raise NotFoundException("Teacher assignment request not found.")

    async def decide_assignment(
        self,
        request_id: uuid.UUID,
        admin_id: uuid.UUID,
        decision: str,
        rejection_reason: str | None = None,
    ) -> dict:
        async def operation():
            request = await self.db.scalar(
                select(TeacherAssignmentRequest)
                .where(TeacherAssignmentRequest.id == request_id)
                .with_for_update()
            )
            if not request:
                raise NotFoundException("Teacher assignment request not found.")
            if request.status != TeacherAssignmentRequestStatus.PENDING.value:
                raise ResourceConflictException("Only pending assignment requests can be decided.")

            teacher = await self.db.get(User, request.teacher_id)
            if not teacher or teacher.role != UserRole.TEACHER:
                raise DomainException("The requested teacher account is invalid.", status_code=422)

            request.decided_by = admin_id
            request.decided_at = self._now()
            request.updated_at = self._now()
            if decision == "approve":
                request.status = TeacherAssignmentRequestStatus.APPROVED.value
                request.rejection_reason = None
                assignment = await self.db.scalar(
                    select(CourseOfferingTeacher).where(
                        CourseOfferingTeacher.course_offering_id == request.course_offering_id,
                        CourseOfferingTeacher.teacher_id == request.teacher_id,
                    )
                )
                if not assignment:
                    self.db.add(
                        CourseOfferingTeacher(
                            course_offering_id=request.course_offering_id,
                            teacher_id=request.teacher_id,
                        )
                    )
            elif decision == "reject":
                request.status = TeacherAssignmentRequestStatus.REJECTED.value
                request.rejection_reason = rejection_reason or "Rejected by the department."
            else:
                raise DomainException("Decision must be approve or reject.", status_code=422)
            await self.db.flush()
            if request.status == TeacherAssignmentRequestStatus.APPROVED.value:
                await self._notify_assignment_approval(request.id)
            return request

        request = await self._run_mutation(
            operation,
            commit=True,
            conflict_message="Could not decide this assignment request.",
        )
        return await self._assignment_request_detail(request.id)

    async def roster(self, offering_id: uuid.UUID) -> list[dict]:
        offering = await self.db.get(CourseOffering, offering_id)
        if not offering:
            raise NotFoundException("Course offering not found.")
        rows = (
            await self.db.execute(
                select(CourseEnrollment, User, Course)
                .join(User, User.id == CourseEnrollment.student_id)
                .join(CourseOffering, CourseOffering.id == CourseEnrollment.course_offering_id)
                .join(Course, Course.id == CourseOffering.course_id)
                .where(
                    CourseEnrollment.course_offering_id == offering_id,
                    CourseEnrollment.status.in_(ACTIVE_ENROLLMENT_STATUSES),
                )
                .order_by(User.full_name)
            )
        ).all()
        return [
            {
                "student_id": enrollment.student_id,
                "identifier": student.identifier,
                "full_name": student.full_name,
                "email": student.email,
                "status": enrollment.status,
                "credit_hours": float(course.credit_hours),
            }
            for enrollment, student, course in rows
        ]

    @staticmethod
    def _enrollment_payload(enrollment, course, semester) -> dict:
        return {
            "id": enrollment.id,
            "course_offering_id": enrollment.course_offering_id,
            "student_id": enrollment.student_id,
            "status": enrollment.status,
            "course_code": course.course_code,
            "course_title": course.title,
            "semester_id": semester.id,
            "semester_title": semester.title,
            "credit_hours": float(course.credit_hours),
            "enrolled_at": enrollment.enrolled_at,
            "updated_at": enrollment.updated_at,
            "dropped_at": enrollment.dropped_at,
        }

    async def list_enrollments(self, student_id: uuid.UUID) -> list[dict]:
        rows = (
            await self.db.execute(
                select(CourseEnrollment, Course, Semester)
                .join(CourseOffering, CourseOffering.id == CourseEnrollment.course_offering_id)
                .join(Course, Course.id == CourseOffering.course_id)
                .join(Semester, Semester.id == CourseOffering.semester_id)
                .where(CourseEnrollment.student_id == student_id)
                .order_by(Semester.start_date.desc(), Course.course_code)
            )
        ).all()
        return [self._enrollment_payload(enrollment, course, semester) for enrollment, course, semester in rows]

    async def active_credit_total(self, student_id: uuid.UUID) -> Decimal:
        total = await self.db.scalar(
            select(func.coalesce(func.sum(Course.credit_hours), 0))
            .select_from(CourseEnrollment)
            .join(CourseOffering, CourseOffering.id == CourseEnrollment.course_offering_id)
            .join(Course, Course.id == CourseOffering.course_id)
            .join(Semester, Semester.id == CourseOffering.semester_id)
            .where(
                CourseEnrollment.student_id == student_id,
                CourseEnrollment.status.in_(ACTIVE_ENROLLMENT_STATUSES),
                Semester.is_active.is_(True),
            )
        )
        return Decimal(str(total or 0))

    async def _enrollment_offerings(
        self,
        offering_ids: Sequence[uuid.UUID],
        *,
        registration: bool = False,
    ) -> dict[uuid.UUID, CourseOffering]:
        rows = (
            await self.db.execute(
                select(CourseOffering)
                .join(Semester, Semester.id == CourseOffering.semester_id)
                .where(
                    CourseOffering.id.in_(offering_ids),
                    CourseOffering.publication_status == OfferingPublicationStatus.PUBLISHED.value,
                    Semester.is_active.is_(True),
                )
                .order_by(CourseOffering.id)
                .with_for_update()
            )
        ).scalars().all()
        offerings = {offering.id: offering for offering in rows}
        if len(offerings) != len(set(offering_ids)):
            message = "All selected course offerings must be published in the active semester."
            raise DomainException(message, status_code=422 if registration else 409)
        return offerings

    async def enroll_many(
        self,
        student_id: uuid.UUID,
        selections: Iterable[tuple[uuid.UUID, str]],
        *,
        commit: bool = True,
        registration: bool = False,
    ) -> list[CourseEnrollment]:
        selection_list = list(selections)
        offering_ids = [offering_id for offering_id, _ in selection_list]
        if len(offering_ids) != len(set(offering_ids)):
            raise DomainException("Duplicate course selections are not allowed.", status_code=422)
        if any(status not in (*ACTIVE_ENROLLMENT_STATUSES, EnrollmentStatus.DROP.value) for _, status in selection_list):
            raise DomainException("Unsupported enrollment status.", status_code=422)
        if not selection_list:
            return []

        async def operation():
            offerings = await self._enrollment_offerings(offering_ids, registration=registration)
            existing_rows = (
                await self.db.execute(
                    select(CourseEnrollment)
                    .where(
                        CourseEnrollment.student_id == student_id,
                        CourseEnrollment.course_offering_id.in_(offering_ids),
                    )
                    .with_for_update()
                )
            ).scalars().all()
            existing = {row.course_offering_id: row for row in existing_rows}
            result = []
            for offering_id, status in selection_list:
                row = existing.get(offering_id)
                if row:
                    if row.status != EnrollmentStatus.DROP.value:
                        raise ResourceConflictException("You are already enrolled in one of the selected offerings.")
                    if status == EnrollmentStatus.DROP.value:
                        raise ResourceConflictException("This enrollment is already dropped.")
                    row.reselect(status)
                    result.append(row)
                    continue
                row = CourseEnrollment(
                    course_offering_id=offerings[offering_id].id,
                    student_id=student_id,
                    status=status,
                )
                self.db.add(row)
                result.append(row)
            await self.db.flush()
            for row in result:
                await self._notify_enrollment(row)
            return result

        return await self._run_mutation(
            operation,
            commit=commit,
            conflict_message="This enrollment already exists or conflicts with a concurrent enrollment.",
        )

    async def enroll(
        self,
        student_id: uuid.UUID,
        offering_id: uuid.UUID,
        enrollment_type: str = EnrollmentStatus.ENROLLED.value,
    ) -> CourseEnrollment:
        rows = await self.enroll_many(student_id, [(offering_id, enrollment_type)])
        return rows[0]

    async def _owned_enrollment_for_update(
        self,
        enrollment_id: int,
        student_id: uuid.UUID,
    ) -> CourseEnrollment:
        enrollment = await self.db.scalar(
            select(CourseEnrollment)
            .where(CourseEnrollment.id == enrollment_id)
            .with_for_update()
        )
        if not enrollment:
            raise NotFoundException("Enrollment not found.")
        if enrollment.student_id != student_id:
            raise ForbiddenException("You may only modify your own enrollments.")
        return enrollment

    async def drop(self, enrollment_id: int, student_id: uuid.UUID) -> CourseEnrollment:
        async def operation():
            enrollment = await self._owned_enrollment_for_update(enrollment_id, student_id)
            if enrollment.status == EnrollmentStatus.DROP.value:
                raise ResourceConflictException("This enrollment is already dropped.")
            enrollment.drop()
            return enrollment

        return await self._run_mutation(
            operation,
            commit=True,
            conflict_message="Could not drop this enrollment.",
        )

    async def reselect(
        self,
        enrollment_id: int,
        student_id: uuid.UUID,
        enrollment_type: str = EnrollmentStatus.ENROLLED.value,
    ) -> CourseEnrollment:
        async def operation():
            enrollment = await self._owned_enrollment_for_update(enrollment_id, student_id)
            if enrollment.status != EnrollmentStatus.DROP.value:
                raise ResourceConflictException("Only dropped enrollments can be reselected.")
            await self._enrollment_offerings([enrollment.course_offering_id])
            enrollment.reselect(enrollment_type)
            await self.db.flush()
            await self._notify_enrollment(enrollment)
            return enrollment

        return await self._run_mutation(
            operation,
            commit=True,
            conflict_message="Could not reselect this enrollment.",
        )
