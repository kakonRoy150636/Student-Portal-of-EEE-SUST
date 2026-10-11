"""Authorization, lifecycle and read models for course workspaces."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, case, exists, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.api.dependencies import verify_course_teacher
from app.core.exceptions import (
    DomainException, ForbiddenException, NotFoundException, ResourceConflictException, UnauthorizedException,
)
from app.models.academic import (
    ACTIVE_ENROLLMENT_STATUSES,
    ClassSchedule,
    Course,
    CourseEnrollment,
    CourseOffering,
    CourseOfferingTeacher,
    Semester,
    TeacherAssignmentRequest,
    TeacherAssignmentRequestStatus,
)
from app.models.course_workspace import (
    ANNOUNCEMENT_AUDIENCES,
    ANNOUNCEMENT_STATUSES,
    ANNOUNCEMENT_TYPES,
    AnnouncementAudience,
    AnnouncementRead,
    AnnouncementStatus,
    AnnouncementType,
    CourseAnnouncement,
    CourseEvent,
    CourseQuestion,
    CourseResource,
)
from app.models.facility import Room
from app.models.notification import NotificationBatch
from app.models.resource import AcademicResource
from app.models.user import User, UserRole
from app.schemas.course_workspace import (
    MAX_ANNOUNCEMENT_BODY,
    MAX_ANNOUNCEMENT_TITLE,
    sanitize_plain_text,
)
from app.services.resource_service import ResourceService
from app.services.notification_service import NotificationService, insert_for

logger = logging.getLogger(__name__)

COURSE_ANNOUNCEMENT_NAMESPACE = uuid.UUID("df32e2b3-3b69-4c15-b8e0-9ccf83a2d8d6")
MAX_FEED_LIMIT = 100
LEARNER_ROLES = (UserRole.STUDENT, UserRole.CR)


def announcement_event_id(announcement_id: uuid.UUID, user_id: uuid.UUID) -> uuid.UUID:
    """Stable notification identity for one announcement recipient pair."""

    return uuid.uuid5(COURSE_ANNOUNCEMENT_NAMESPACE, f"{announcement_id}:{user_id}")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _safe_announcement_text(value: str, field_name: str, maximum: int) -> str:
    cleaned = sanitize_plain_text(value)
    if not cleaned:
        raise DomainException(f"{field_name} must not be blank.", status_code=422)
    if len(cleaned) > maximum:
        raise DomainException(f"{field_name} must be at most {maximum} characters.", status_code=422)
    return cleaned


class CourseWorkspaceService:
    """Keep course workspace rules in one transaction-aware service."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._pending_notification_batches: set[uuid.UUID] = set()

    async def _run_mutation(self, operation):
        try:
            result = await operation()
            await self.db.flush()
            await self.db.commit()
            self._publish_pending_notifications()
            return result
        except IntegrityError as exc:
            self._pending_notification_batches.clear()
            await self.db.rollback()
            raise ResourceConflictException("The course workspace change conflicts with existing data.") from exc
        except Exception:
            self._pending_notification_batches.clear()
            await self.db.rollback()
            raise

    def _publish_pending_notifications(self) -> None:
        batch_ids = tuple(self._pending_notification_batches)
        self._pending_notification_batches.clear()
        if not batch_ids:
            return
        try:
            from app.tasks.notifications import deliver_notification
        except Exception:
            logger.warning("Could not load course announcement publisher; outbox will recover it.")
            return
        for batch_id in batch_ids:
            try:
                deliver_notification.delay(str(batch_id))
            except Exception:
                logger.warning("Could not publish course announcement batch; outbox will recover it.")

    async def _offering_context(self, offering_id: uuid.UUID):
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
        return row

    async def _has_active_enrollment(self, offering_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        value = await self.db.scalar(
            select(CourseEnrollment.id)
            .join(CourseOffering, CourseOffering.id == CourseEnrollment.course_offering_id)
            .join(Semester, Semester.id == CourseOffering.semester_id)
            .join(User, User.id == CourseEnrollment.student_id)
            .where(
                CourseEnrollment.course_offering_id == offering_id,
                CourseEnrollment.student_id == user_id,
                CourseEnrollment.status.in_(ACTIVE_ENROLLMENT_STATUSES),
                User.is_active.is_(True),
                CourseOffering.publication_status == "published",
                Semester.is_active.is_(True),
            )
        )
        return value is not None

    async def _authorize_offering(self, offering_id: uuid.UUID, user: User, *, manager_only: bool = False):
        if not user.is_active:
            raise UnauthorizedException("User not active.")
        context = await self._offering_context(offering_id)
        if user.role in (UserRole.SUPER_ADMIN, UserRole.TEACHER):
            await verify_course_teacher(offering_id, user, self.db)
            return context, True

        if manager_only or user.role not in LEARNER_ROLES:
            raise ForbiddenException("This account cannot access the course workspace.")
        if not await self._has_active_enrollment(offering_id, user.id):
            raise ForbiddenException("An active enrollment is required for this course workspace.")
        return context, False

    async def require_manager(self, offering_id: uuid.UUID, user: User):
        return await self._authorize_offering(offering_id, user, manager_only=True)

    @staticmethod
    def _validate_enum_values(*, announcement_type: str, status: str, audience: str) -> None:
        if announcement_type not in ANNOUNCEMENT_TYPES:
            raise DomainException("Unsupported announcement type.", status_code=422)
        if status not in ANNOUNCEMENT_STATUSES:
            raise DomainException("Unsupported announcement status.", status_code=422)
        if audience not in ANNOUNCEMENT_AUDIENCES:
            raise DomainException("Unsupported announcement audience.", status_code=422)

    @staticmethod
    def _validate_schedule(status: str, publish_at: datetime | None, now: datetime, *, allow_published_without_time: bool = False) -> datetime | None:
        publish_at = _as_utc(publish_at) if publish_at is not None else None
        if status == AnnouncementStatus.DRAFT.value:
            if publish_at is not None:
                raise DomainException("Draft announcements cannot have publish_at.", status_code=422)
            return None
        if status == AnnouncementStatus.SCHEDULED.value:
            if publish_at is None or publish_at <= now:
                raise DomainException("Scheduled announcements require a future publish_at.", status_code=422)
            return publish_at
        if status == AnnouncementStatus.PUBLISHED.value:
            if publish_at is None and allow_published_without_time:
                return now
            if publish_at is not None and publish_at > now:
                raise DomainException("Published announcements cannot have a future publish_at.", status_code=422)
            return publish_at or now
        if status == AnnouncementStatus.ARCHIVED.value:
            return publish_at
        raise DomainException("Unsupported announcement status.", status_code=422)

    async def _active_recipients(self, announcement: CourseAnnouncement) -> list[uuid.UUID]:
        if announcement.audience == AnnouncementAudience.TEACHERS_ONLY.value:
            request = aliased(TeacherAssignmentRequest)
            assigned_stmt = (
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
                    CourseOfferingTeacher.course_offering_id == announcement.offering_id,
                    User.role == UserRole.TEACHER,
                    User.is_active.is_(True),
                    or_(request.id.is_(None), request.status == TeacherAssignmentRequestStatus.APPROVED.value),
                )
                .distinct()
                .order_by(User.id)
            )
            assigned = set((await self.db.scalars(assigned_stmt)).all())
            approved_stmt = (
                select(User.id)
                .join(request, request.teacher_id == User.id)
                .where(
                    request.course_offering_id == announcement.offering_id,
                    request.status == TeacherAssignmentRequestStatus.APPROVED.value,
                    User.role == UserRole.TEACHER,
                    User.is_active.is_(True),
                )
                .order_by(User.id)
            )
            assigned.update((await self.db.scalars(approved_stmt)).all())
            return sorted(assigned)

        roles = [UserRole.CR] if announcement.audience == AnnouncementAudience.CR_ONLY.value else [UserRole.STUDENT, UserRole.CR]
        stmt = (
            select(User.id)
            .join(CourseEnrollment, CourseEnrollment.student_id == User.id)
            .join(CourseOffering, CourseOffering.id == CourseEnrollment.course_offering_id)
            .join(Semester, Semester.id == CourseOffering.semester_id)
            .where(
                CourseEnrollment.course_offering_id == announcement.offering_id,
                CourseEnrollment.status.in_(ACTIVE_ENROLLMENT_STATUSES),
                User.role.in_(roles),
                User.is_active.is_(True),
                CourseOffering.publication_status == "published",
                Semester.is_active.is_(True),
            )
            .distinct()
            .order_by(User.id)
        )
        return list((await self.db.scalars(stmt)).all())

    async def _enqueue_announcement_notifications(self, announcement: CourseAnnouncement, now: datetime | None = None) -> None:
        priority = "high" if announcement.announcement_type == AnnouncementType.URGENT.value else "medium"
        service = NotificationService(self.db)
        for user_id in await self._active_recipients(announcement):
            result = await service.enqueue_course_announcement(
                user_id,
                announcement_event_id(announcement.id, user_id),
                announcement.offering_id,
                announcement.id,
                priority,
                now=now,
            )
            if result and result[1]:
                batch = await self.db.get(NotificationBatch, result[1])
                if batch is not None and batch.status == "pending":
                    self._pending_notification_batches.add(result[1])

    async def publish_due_announcements(self, now: datetime | None = None, *, limit: int = 100) -> int:
        """Durably publish due schedules; concurrent workers skip claimed rows.

        The existing minute-level Celery Beat runner invokes this method. The
        status transition and recipient outbox entries commit together, so a
        worker retry cannot duplicate a publish or leave a notification orphan.
        """
        now = _as_utc(now or _utcnow())

        async def operation():
            rows = (await self.db.scalars(
                select(CourseAnnouncement)
                .join(CourseOffering, CourseOffering.id == CourseAnnouncement.offering_id)
                .join(Semester, Semester.id == CourseOffering.semester_id)
                .where(
                    CourseAnnouncement.status == AnnouncementStatus.SCHEDULED.value,
                    CourseAnnouncement.publish_at <= now,
                    CourseOffering.publication_status == "published",
                    Semester.is_active.is_(True),
                )
                .order_by(CourseAnnouncement.publish_at, CourseAnnouncement.id)
                .with_for_update(skip_locked=True, of=CourseAnnouncement)
                .execution_options(populate_existing=True)
                .limit(limit)
            )).all()
            for announcement in rows:
                announcement.status = AnnouncementStatus.PUBLISHED.value
                announcement.updated_at = now
                await self.db.flush()
                await self._enqueue_announcement_notifications(announcement, now)
            return len(rows)

        return await self._run_mutation(operation)

    @staticmethod
    def _permissions(manager: bool) -> dict[str, bool]:
        return {
            "can_manage": manager,
            "can_publish": manager,
            "can_edit": manager,
            "can_archive": manager,
            "can_pin": manager,
        }

    @classmethod
    def _announcement_permissions(cls, announcement: CourseAnnouncement, manager: bool) -> dict[str, bool]:
        permissions = cls._permissions(manager)
        if announcement.status == AnnouncementStatus.ARCHIVED.value:
            permissions.update(can_publish=False, can_edit=False, can_archive=False, can_pin=False)
        elif announcement.status == AnnouncementStatus.PUBLISHED.value:
            permissions["can_publish"] = False
        return permissions

    @classmethod
    def _announcement_payload(
        cls,
        announcement: CourseAnnouncement,
        author_name: str,
        is_read: bool,
        manager: bool,
    ) -> dict[str, Any]:
        return {
            "id": announcement.id,
            "offering_id": announcement.offering_id,
            "author_id": announcement.author_id,
            "author_name": author_name,
            "title": announcement.title,
            "body": announcement.body,
            "announcement_type": announcement.announcement_type,
            "status": announcement.status,
            "audience": announcement.audience,
            "is_pinned": bool(announcement.is_pinned),
            "publish_at": announcement.publish_at,
            "created_at": announcement.created_at,
            "updated_at": announcement.updated_at,
            "archived_at": announcement.archived_at,
            "is_read": is_read,
            **cls._announcement_permissions(announcement, manager),
        }

    @staticmethod
    def _student_visibility(announcement: CourseAnnouncement, user: User, now: datetime) -> bool:
        if announcement.status != AnnouncementStatus.PUBLISHED.value:
            return False
        if announcement.publish_at is not None and _as_utc(announcement.publish_at) > now:
            return False
        if announcement.audience == AnnouncementAudience.TEACHERS_ONLY.value:
            return False
        if announcement.audience == AnnouncementAudience.CR_ONLY.value and user.role != UserRole.CR:
            return False
        return True

    async def list_announcements(
        self,
        offering_id: uuid.UUID,
        user: User,
        *,
        limit: int = 20,
        offset: int = 0,
        search: str | None = None,
        status: str | None = None,
        announcement_type: str | None = None,
    ) -> dict[str, Any]:
        _, manager = await self._authorize_offering(offering_id, user)
        if limit < 1 or limit > MAX_FEED_LIMIT:
            raise DomainException("limit must be between 1 and 100.", status_code=422)
        if offset < 0:
            raise DomainException("offset must be non-negative.", status_code=422)
        if status is not None and status not in ANNOUNCEMENT_STATUSES:
            raise DomainException("Unsupported announcement status.", status_code=422)
        if announcement_type is not None and announcement_type not in ANNOUNCEMENT_TYPES:
            raise DomainException("Unsupported announcement type.", status_code=422)

        now = _utcnow()
        conditions = [CourseAnnouncement.offering_id == offering_id]
        if manager:
            if status is not None:
                conditions.append(CourseAnnouncement.status == status)
        else:
            conditions.extend(
                [
                    CourseAnnouncement.status == AnnouncementStatus.PUBLISHED.value,
                    or_(CourseAnnouncement.publish_at.is_(None), CourseAnnouncement.publish_at <= now),
                ]
            )
            if user.role == UserRole.CR:
                conditions.append(
                    CourseAnnouncement.audience.in_(
                        [AnnouncementAudience.ENROLLED_STUDENTS.value, AnnouncementAudience.CR_ONLY.value]
                    )
                )
            else:
                conditions.append(CourseAnnouncement.audience == AnnouncementAudience.ENROLLED_STUDENTS.value)
            if status is not None:
                # Keep caller-requested filtering semantics without allowing a
                # non-published status to bypass the learner visibility gate.
                conditions.append(CourseAnnouncement.status == status)
        if announcement_type is not None:
            conditions.append(CourseAnnouncement.announcement_type == announcement_type)
        if search:
            pattern = f"%{_escape_like(search.strip())}%"
            conditions.append(
                or_(
                    CourseAnnouncement.title.ilike(pattern, escape="\\"),
                    CourseAnnouncement.body.ilike(pattern, escape="\\"),
                )
            )

        total = int(await self.db.scalar(select(func.count()).select_from(CourseAnnouncement).where(*conditions)) or 0)
        rows = (
            await self.db.execute(
                select(CourseAnnouncement, User.full_name)
                .join(User, User.id == CourseAnnouncement.author_id)
                .where(*conditions)
                .order_by(
                    CourseAnnouncement.is_pinned.desc(),
                    CourseAnnouncement.publish_at.desc().nullslast(),
                    CourseAnnouncement.created_at.desc(),
                    CourseAnnouncement.id.desc(),
                )
                .offset(offset)
                .limit(limit)
            )
        ).all()
        read_ids: set[uuid.UUID] = set()
        if rows:
            read_ids = set(
                (
                    await self.db.scalars(
                        select(AnnouncementRead.announcement_id).where(
                            AnnouncementRead.user_id == user.id,
                            AnnouncementRead.announcement_id.in_([row[0].id for row in rows]),
                        )
                    )
                ).all()
            )
        items = [
            self._announcement_payload(announcement, author_name, announcement.id in read_ids, manager)
            for announcement, author_name in rows
        ]
        return {"items": items, "total": total, "limit": limit, "offset": offset, "has_more": offset + len(items) < total}

    async def _announcement_with_author(self, announcement_id: uuid.UUID, offering_id: uuid.UUID | None = None):
        conditions = [CourseAnnouncement.id == announcement_id]
        if offering_id is not None:
            conditions.append(CourseAnnouncement.offering_id == offering_id)
        row = (
            await self.db.execute(
                select(CourseAnnouncement, User.full_name)
                .join(User, User.id == CourseAnnouncement.author_id)
                .where(*conditions)
            )
        ).one_or_none()
        if not row:
            raise NotFoundException("Course announcement not found.")
        return row

    async def get_announcement(self, offering_id: uuid.UUID, announcement_id: uuid.UUID, user: User) -> dict[str, Any]:
        announcement, author_name = await self._announcement_with_author(announcement_id, offering_id)
        _, manager = await self._authorize_offering(offering_id, user)
        if not manager and not self._student_visibility(announcement, user, _utcnow()):
            raise NotFoundException("Course announcement not found.")
        read = await self.db.scalar(
            select(AnnouncementRead.announcement_id).where(
                AnnouncementRead.announcement_id == announcement.id,
                AnnouncementRead.user_id == user.id,
            )
        )
        return self._announcement_payload(announcement, author_name, read is not None, manager)

    async def _lock_announcement(self, offering_id: uuid.UUID, announcement_id: uuid.UUID) -> CourseAnnouncement:
        announcement = await self.db.scalar(
            select(CourseAnnouncement)
            .where(
                CourseAnnouncement.id == announcement_id,
                CourseAnnouncement.offering_id == offering_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if announcement is None:
            raise NotFoundException("Course announcement not found.")
        return announcement

    async def create_announcement(self, offering_id: uuid.UUID, user: User, payload) -> dict[str, Any]:
        await self.require_manager(offering_id, user)

        async def operation():
            await self.db.execute(select(CourseOffering.id).where(CourseOffering.id == offering_id).with_for_update())
            now = _utcnow()
            status = payload.status
            self._validate_enum_values(
                announcement_type=payload.announcement_type,
                status=status,
                audience=payload.audience,
            )
            publish_at = self._validate_schedule(
                status,
                payload.publish_at,
                now,
                allow_published_without_time=True,
            )
            announcement = CourseAnnouncement(
                offering_id=offering_id,
                author_id=user.id,
                title=_safe_announcement_text(payload.title, "Title", MAX_ANNOUNCEMENT_TITLE),
                body=_safe_announcement_text(payload.body, "Body", MAX_ANNOUNCEMENT_BODY),
                announcement_type=payload.announcement_type,
                status=status,
                audience=payload.audience,
                publish_at=publish_at,
            )
            self.db.add(announcement)
            await self.db.flush()
            if status == AnnouncementStatus.PUBLISHED.value:
                await self._enqueue_announcement_notifications(announcement)
            return announcement

        announcement = await self._run_mutation(operation)
        return await self.get_announcement(offering_id, announcement.id, user)

    async def update_announcement(self, offering_id: uuid.UUID, announcement_id: uuid.UUID, user: User, payload) -> dict[str, Any]:
        await self.require_manager(offering_id, user)
        changes = payload.model_dump(exclude_unset=True)

        async def operation():
            announcement = await self._lock_announcement(offering_id, announcement_id)
            if announcement.status == AnnouncementStatus.ARCHIVED.value:
                raise ResourceConflictException("Archived announcements cannot be edited.")
            now = _utcnow()
            next_type = changes.get("announcement_type", announcement.announcement_type)
            next_audience = changes.get("audience", announcement.audience)
            next_status = changes.get("status", announcement.status)
            next_publish_at = changes.get("publish_at", announcement.publish_at)
            self._validate_enum_values(announcement_type=next_type, status=next_status, audience=next_audience)
            if announcement.status == AnnouncementStatus.PUBLISHED.value and next_status != announcement.status:
                raise ResourceConflictException("Published announcements can only be archived or edited in place.")
            if next_status == AnnouncementStatus.DRAFT.value and "publish_at" not in changes:
                next_publish_at = None
            if next_status == AnnouncementStatus.PUBLISHED.value and "publish_at" not in changes and announcement.status != next_status:
                next_publish_at = now
            if next_status == AnnouncementStatus.PUBLISHED.value and announcement.status != AnnouncementStatus.PUBLISHED.value:
                next_publish_at = self._validate_schedule(next_status, next_publish_at, now, allow_published_without_time=True)
            else:
                next_publish_at = self._validate_schedule(next_status, next_publish_at, now)
            if "title" in changes:
                announcement.title = _safe_announcement_text(changes["title"], "Title", MAX_ANNOUNCEMENT_TITLE)
            if "body" in changes:
                announcement.body = _safe_announcement_text(changes["body"], "Body", MAX_ANNOUNCEMENT_BODY)
            if "announcement_type" in changes:
                announcement.announcement_type = next_type
            if "audience" in changes:
                announcement.audience = next_audience
            previous_status = announcement.status
            announcement.status = next_status
            announcement.publish_at = next_publish_at
            announcement.updated_at = now
            if next_status == AnnouncementStatus.PUBLISHED.value:
                announcement.archived_at = None
            if previous_status != AnnouncementStatus.PUBLISHED.value and next_status == AnnouncementStatus.PUBLISHED.value:
                await self.db.flush()
                await self._enqueue_announcement_notifications(announcement)
            return announcement

        await self._run_mutation(operation)
        return await self.get_announcement(offering_id, announcement_id, user)

    async def publish_announcement(self, offering_id: uuid.UUID, announcement_id: uuid.UUID, user: User) -> dict[str, Any]:
        await self.require_manager(offering_id, user)

        async def operation():
            announcement = await self._lock_announcement(offering_id, announcement_id)
            if announcement.status == AnnouncementStatus.ARCHIVED.value:
                raise ResourceConflictException("Archived announcements cannot be published.")
            if announcement.status == AnnouncementStatus.PUBLISHED.value:
                return announcement
            now = _utcnow()
            announcement.status = AnnouncementStatus.PUBLISHED.value
            announcement.publish_at = now
            announcement.archived_at = None
            announcement.updated_at = now
            await self.db.flush()
            await self._enqueue_announcement_notifications(announcement)
            return announcement

        await self._run_mutation(operation)
        return await self.get_announcement(offering_id, announcement_id, user)

    async def archive_announcement(self, offering_id: uuid.UUID, announcement_id: uuid.UUID, user: User) -> dict[str, Any]:
        await self.require_manager(offering_id, user)

        async def operation():
            announcement = await self._lock_announcement(offering_id, announcement_id)
            if announcement.status != AnnouncementStatus.ARCHIVED.value:
                now = _utcnow()
                announcement.status = AnnouncementStatus.ARCHIVED.value
                announcement.archived_at = now
                announcement.is_pinned = False
                announcement.updated_at = now
            return announcement

        await self._run_mutation(operation)
        return await self.get_announcement(offering_id, announcement_id, user)

    async def pin_announcement(
        self,
        offering_id: uuid.UUID,
        announcement_id: uuid.UUID,
        user: User,
        pinned: bool,
    ) -> dict[str, Any]:
        await self.require_manager(offering_id, user)

        async def operation():
            announcement = await self._lock_announcement(offering_id, announcement_id)
            if announcement.status == AnnouncementStatus.ARCHIVED.value and pinned:
                raise ResourceConflictException("Archived announcements cannot be pinned.")
            if bool(announcement.is_pinned) != pinned:
                announcement.is_pinned = pinned
                announcement.updated_at = _utcnow()
            return announcement

        await self._run_mutation(operation)
        return await self.get_announcement(offering_id, announcement_id, user)

    async def mark_read(self, announcement_id: uuid.UUID, user: User) -> dict[str, Any]:
        announcement, _ = await self._announcement_with_author(announcement_id)
        _, manager = await self._authorize_offering(announcement.offering_id, user)
        if not manager and not self._student_visibility(announcement, user, _utcnow()):
            raise NotFoundException("Course announcement not found.")

        async def operation():
            now = _utcnow()
            await self.db.execute(
                insert_for(self.db, AnnouncementRead)
                .values(announcement_id=announcement_id, user_id=user.id, read_at=now)
                .on_conflict_do_nothing(index_elements=[AnnouncementRead.announcement_id, AnnouncementRead.user_id])
            )
            return await self.db.get(AnnouncementRead, (announcement_id, user.id))

        row = await self._run_mutation(operation)
        return {"announcement_id": row.announcement_id, "read_at": row.read_at, "is_read": True}

    async def _authorized_teachers(self, offering_id: uuid.UUID) -> list[dict[str, Any]]:
        request = aliased(TeacherAssignmentRequest)
        rows = (
            await self.db.execute(
                select(User.id, User.full_name, CourseOfferingTeacher.role)
                .join(User, User.id == CourseOfferingTeacher.teacher_id)
                .outerjoin(
                    request,
                    and_(
                        request.course_offering_id == CourseOfferingTeacher.course_offering_id,
                        request.teacher_id == CourseOfferingTeacher.teacher_id,
                    ),
                )
                .where(
                    CourseOfferingTeacher.course_offering_id == offering_id,
                    User.role == UserRole.TEACHER,
                    User.is_active.is_(True),
                    or_(request.id.is_(None), request.status == TeacherAssignmentRequestStatus.APPROVED.value),
                )
                .order_by(User.full_name, User.id)
            )
        ).all()
        details = {teacher_id: {"teacher_id": teacher_id, "teacher_name": name, "role": role} for teacher_id, name, role in rows}
        approved_only = (
            await self.db.execute(
                select(User.id, User.full_name)
                .join(TeacherAssignmentRequest, TeacherAssignmentRequest.teacher_id == User.id)
                .where(
                    TeacherAssignmentRequest.course_offering_id == offering_id,
                    TeacherAssignmentRequest.status == TeacherAssignmentRequestStatus.APPROVED.value,
                    User.role == UserRole.TEACHER,
                    User.is_active.is_(True),
                )
                .order_by(User.full_name, User.id)
            )
        ).all()
        for teacher_id, name in approved_only:
            details.setdefault(
                teacher_id,
                {"teacher_id": teacher_id, "teacher_name": name, "role": "course_teacher"},
            )
        provider = (await self.db.execute(
            select(User.id, User.full_name)
            .join(CourseOffering, CourseOffering.created_by == User.id)
            .where(CourseOffering.id == offering_id, User.is_active.is_(True), User.role == UserRole.TEACHER)
        )).one_or_none()
        if provider is not None:
            details.setdefault(provider.id, {"teacher_id": provider.id, "teacher_name": provider.full_name, "role": "provider"})
        return sorted(details.values(), key=lambda item: (item["teacher_name"], item["teacher_id"]))

    async def _visible_unread_count(self, offering_id: uuid.UUID, user: User, manager: bool) -> int:
        conditions = [
            CourseAnnouncement.offering_id == offering_id,
            CourseAnnouncement.status == AnnouncementStatus.PUBLISHED.value,
            or_(CourseAnnouncement.publish_at.is_(None), CourseAnnouncement.publish_at <= _utcnow()),
        ]
        if not manager:
            if user.role == UserRole.CR:
                conditions.append(
                    CourseAnnouncement.audience.in_(
                        [AnnouncementAudience.ENROLLED_STUDENTS.value, AnnouncementAudience.CR_ONLY.value]
                    )
                )
            else:
                conditions.append(CourseAnnouncement.audience == AnnouncementAudience.ENROLLED_STUDENTS.value)
        read_exists = exists(
            select(AnnouncementRead.announcement_id).where(
                AnnouncementRead.announcement_id == CourseAnnouncement.id,
                AnnouncementRead.user_id == user.id,
            )
        )
        return int(
            await self.db.scalar(
                select(func.count()).select_from(CourseAnnouncement).where(*conditions, ~read_exists)
            )
            or 0
        )

    async def _schedules(self, offering_id: uuid.UUID) -> list[dict[str, Any]]:
        day_order = case(
            (ClassSchedule.day_of_week.ilike("monday"), 1),
            (ClassSchedule.day_of_week.ilike("tuesday"), 2),
            (ClassSchedule.day_of_week.ilike("wednesday"), 3),
            (ClassSchedule.day_of_week.ilike("thursday"), 4),
            (ClassSchedule.day_of_week.ilike("friday"), 5),
            (ClassSchedule.day_of_week.ilike("saturday"), 6),
            (ClassSchedule.day_of_week.ilike("sunday"), 7),
            else_=8,
        )
        rows = (
            await self.db.execute(
                select(ClassSchedule, Room.room_number, Room.is_lab, User.full_name)
                .join(Room, Room.id == ClassSchedule.room_id)
                .outerjoin(User, User.id == ClassSchedule.instructor_id)
                .where(ClassSchedule.course_offering_id == offering_id)
                .order_by(day_order, ClassSchedule.start_time, ClassSchedule.id)
            )
        ).all()
        return [
            {
                "id": schedule.id,
                "day_of_week": schedule.day_of_week,
                "start_time": schedule.start_time.strftime("%H:%M:%S"),
                "end_time": schedule.end_time.strftime("%H:%M:%S"),
                "room_number": room_number,
                "instructor_name": instructor_name,
                "is_lab": bool(is_lab) if is_lab is not None else None,
            }
            for schedule, room_number, is_lab, instructor_name in rows
        ]

    async def list_resources(self, offering_id: uuid.UUID, user: User) -> list[dict[str, Any]]:
        _, manager = await self._authorize_offering(offering_id, user)
        offering = await self.db.scalar(select(CourseOffering).where(CourseOffering.id == offering_id))
        assert offering is not None
        conditions = [AcademicResource.course_id == offering.course_id]
        if not manager:
            conditions.append(
                or_(
                    CourseResource.id.is_(None),
                    and_(CourseResource.is_published.is_(True), CourseResource.archived_at.is_(None)),
                )
            )
        rows = (
            await self.db.execute(
                select(AcademicResource, CourseResource)
                .outerjoin(
                    CourseResource,
                    and_(
                        CourseResource.resource_id == AcademicResource.id,
                        CourseResource.offering_id == offering_id,
                    ),
                )
                .where(*conditions)
                .order_by(AcademicResource.created_at.desc(), AcademicResource.id.desc())
            )
        ).all()
        return [
            {
                "id": resource.id,
                "title": resource.title,
                "description": resource.description,
                "category": resource.category,
                "course_id": resource.course_id,
                "file_name": resource.file_name,
                "file_size_bytes": resource.file_size_bytes,
                "mime_type": resource.mime_type,
                "download_count": resource.download_count or 0,
                "is_faculty_verified": bool(resource.is_faculty_verified),
                "created_at": resource.created_at,
                "is_published": bool(link.is_published) if link is not None else True,
                "archived_at": link.archived_at if link is not None else None,
                "can_manage": manager,
            }
            for resource, link in rows
        ]

    async def update_resource(
        self,
        offering_id: uuid.UUID,
        resource_id: uuid.UUID,
        user: User,
        *,
        is_published: bool | None = None,
        archived: bool | None = None,
    ) -> dict[str, Any]:
        await self.require_manager(offering_id, user)
        offering = await self.db.scalar(select(CourseOffering).where(CourseOffering.id == offering_id))
        if offering is None:
            raise NotFoundException("Course offering not found.")

        async def operation():
            resource = await self.db.scalar(
                select(AcademicResource).where(
                    AcademicResource.id == resource_id,
                    AcademicResource.course_id == offering.course_id,
                )
            )
            if resource is None:
                raise NotFoundException("Course resource not found.")
            link = await self.db.scalar(
                select(CourseResource)
                .where(CourseResource.offering_id == offering_id, CourseResource.resource_id == resource_id)
                .with_for_update()
            )
            if link is None:
                link = CourseResource(
                    offering_id=offering_id,
                    resource_id=resource_id,
                    published_by=user.id,
                    is_published=True,
                )
                self.db.add(link)
                await self.db.flush()
            if is_published is not None:
                link.is_published = is_published
            if archived is True:
                link.archived_at = _utcnow()
                link.is_published = False
            elif archived is False:
                link.archived_at = None
            link.updated_at = _utcnow()
            return resource

        await self._run_mutation(operation)
        return next(item for item in await self.list_resources(offering_id, user) if item["id"] == resource_id)

    async def finalize_resource_upload(self, offering_id: uuid.UUID, user: User, payload):
        await self.require_manager(offering_id, user)
        offering, course, _ = await self._offering_context(offering_id)
        if payload.course_code.strip().upper() != course.course_code:
            raise DomainException("The resource course code does not match this offering.", status_code=422)
        resource = await ResourceService(self.db).finalize_upload(payload, user)
        self.db.add(CourseResource(
            offering_id=offering.id,
            resource_id=resource.id,
            published_by=user.id,
            is_published=True,
        ))
        await self.db.commit()
        await self.db.refresh(resource)
        return resource

    @staticmethod
    def _event_payload(event: CourseEvent, author_name: str, manager: bool) -> dict[str, Any]:
        return {
            "id": event.id,
            "offering_id": event.offering_id,
            "author_id": event.author_id,
            "author_name": author_name,
            "title": event.title,
            "description": event.description,
            "event_type": event.event_type,
            "starts_at": event.starts_at,
            "ends_at": event.ends_at,
            "location": event.location,
            "reminder_minutes": event.reminder_minutes,
            "is_published": bool(event.is_published),
            "archived_at": event.archived_at,
            "created_at": event.created_at,
            "updated_at": event.updated_at,
            "can_manage": manager,
        }

    async def list_events(self, offering_id: uuid.UUID, user: User) -> list[dict[str, Any]]:
        _, manager = await self._authorize_offering(offering_id, user)
        conditions = [CourseEvent.offering_id == offering_id, CourseEvent.archived_at.is_(None)]
        if not manager:
            conditions.append(CourseEvent.is_published.is_(True))
        rows = (
            await self.db.execute(
                select(CourseEvent, User.full_name)
                .join(User, User.id == CourseEvent.author_id)
                .where(*conditions)
                .order_by(CourseEvent.starts_at, CourseEvent.id)
            )
        ).all()
        return [self._event_payload(event, author_name, manager) for event, author_name in rows]

    async def create_event(self, offering_id: uuid.UUID, user: User, payload) -> dict[str, Any]:
        await self.require_manager(offering_id, user)

        async def operation():
            event = CourseEvent(
                offering_id=offering_id,
                author_id=user.id,
                title=sanitize_plain_text(payload.title),
                description=sanitize_plain_text(payload.description) if payload.description else None,
                event_type=payload.event_type,
                starts_at=_as_utc(payload.starts_at),
                ends_at=_as_utc(payload.ends_at) if payload.ends_at else None,
                location=sanitize_plain_text(payload.location) if payload.location else None,
                reminder_minutes=payload.reminder_minutes,
                is_published=payload.is_published,
            )
            self.db.add(event)
            await self.db.flush()
            return event

        event = await self._run_mutation(operation)
        return next(item for item in await self.list_events(offering_id, user) if item["id"] == event.id)

    async def update_event(self, offering_id: uuid.UUID, event_id: uuid.UUID, user: User, payload) -> dict[str, Any]:
        await self.require_manager(offering_id, user)
        changes = payload.model_dump(exclude_unset=True)

        async def operation():
            event = await self.db.scalar(
                select(CourseEvent)
                .where(CourseEvent.id == event_id, CourseEvent.offering_id == offering_id)
                .with_for_update()
            )
            if event is None:
                raise NotFoundException("Course event not found.")
            if event.archived_at is not None:
                raise ResourceConflictException("Archived course events cannot be edited.")
            for field in ("title", "event_type", "reminder_minutes", "is_published"):
                if field in changes and changes[field] is not None:
                    setattr(event, field, changes[field])
            if "description" in changes:
                event.description = sanitize_plain_text(changes["description"]) if changes["description"] else None
            if "location" in changes:
                event.location = sanitize_plain_text(changes["location"]) if changes["location"] else None
            if "starts_at" in changes and changes["starts_at"] is not None:
                event.starts_at = _as_utc(changes["starts_at"])
            if "ends_at" in changes:
                event.ends_at = _as_utc(changes["ends_at"]) if changes["ends_at"] else None
            if event.ends_at is not None and event.ends_at < event.starts_at:
                raise DomainException("Event end must not be before its start.", status_code=422)
            event.updated_at = _utcnow()
            return event

        await self._run_mutation(operation)
        return next(item for item in await self.list_events(offering_id, user) if item["id"] == event_id)

    async def archive_event(self, offering_id: uuid.UUID, event_id: uuid.UUID, user: User) -> dict[str, Any]:
        await self.require_manager(offering_id, user)

        async def operation():
            event = await self.db.scalar(
                select(CourseEvent)
                .where(CourseEvent.id == event_id, CourseEvent.offering_id == offering_id)
                .with_for_update()
            )
            if event is None:
                raise NotFoundException("Course event not found.")
            event.archived_at = _utcnow()
            event.is_published = False
            event.updated_at = _utcnow()
            return event

        await self._run_mutation(operation)
        return {"id": event_id, "archived": True}

    @staticmethod
    def _question_payload(question: CourseQuestion, student_name: str, manager: bool, user: User) -> dict[str, Any]:
        return {
            "id": question.id,
            "offering_id": question.offering_id,
            "student_id": question.student_id,
            "student_name": student_name,
            "title": question.title,
            "body": question.body,
            "status": question.status,
            "visibility": question.visibility,
            "answer_body": question.answer_body,
            "answered_by": question.answered_by,
            "answered_at": question.answered_at,
            "resolved_at": question.resolved_at,
            "created_at": question.created_at,
            "updated_at": question.updated_at,
            "can_manage": manager,
            "can_answer": manager and question.status not in {"resolved", "closed"},
            "can_edit": not manager and question.student_id == user.id and question.status == "open",
        }

    async def list_questions(self, offering_id: uuid.UUID, user: User) -> list[dict[str, Any]]:
        _, manager = await self._authorize_offering(offering_id, user)
        conditions = [CourseQuestion.offering_id == offering_id]
        if not manager:
            conditions.append(
                or_(
                    CourseQuestion.visibility == "course",
                    CourseQuestion.student_id == user.id,
                )
            )
        rows = (
            await self.db.execute(
                select(CourseQuestion, User.full_name)
                .join(User, User.id == CourseQuestion.student_id)
                .where(*conditions)
                .order_by(CourseQuestion.created_at.desc(), CourseQuestion.id.desc())
            )
        ).all()
        return [self._question_payload(question, student_name, manager, user) for question, student_name in rows]

    async def create_question(self, offering_id: uuid.UUID, user: User, payload) -> dict[str, Any]:
        if user.role not in LEARNER_ROLES:
            raise ForbiddenException("Only enrolled students can ask course questions.")
        await self._authorize_offering(offering_id, user)
        question = CourseQuestion(
            offering_id=offering_id,
            student_id=user.id,
            title=sanitize_plain_text(payload.title),
            body=sanitize_plain_text(payload.body),
            visibility=payload.visibility,
        )
        self.db.add(question)
        await self.db.commit()
        await self.db.refresh(question)
        return (await self.list_questions(offering_id, user))[-1]

    async def answer_question(self, offering_id: uuid.UUID, question_id: uuid.UUID, user: User, payload) -> dict[str, Any]:
        await self.require_manager(offering_id, user)

        async def operation():
            question = await self.db.scalar(
                select(CourseQuestion)
                .where(CourseQuestion.id == question_id, CourseQuestion.offering_id == offering_id)
                .with_for_update()
            )
            if question is None:
                raise NotFoundException("Course question not found.")
            now = _utcnow()
            question.answer_body = sanitize_plain_text(payload.answer_body)
            question.answered_by = user.id
            question.answered_at = now
            question.status = payload.status
            question.resolved_at = now if payload.status in {"resolved", "closed"} else None
            question.updated_at = now
            result = await NotificationService(self.db).enqueue(
                question.student_id,
                uuid.uuid5(COURSE_ANNOUNCEMENT_NAMESPACE, f"question-answer:{question.id}"),
                "announcement",
                "high",
                now,
            )
            if result and result[1]:
                batch = await self.db.get(NotificationBatch, result[1])
                if batch is not None and batch.status == "pending":
                    self._pending_notification_batches.add(result[1])
            return question

        await self._run_mutation(operation)
        return next(item for item in await self.list_questions(offering_id, user) if item["id"] == question_id)

    async def workspace(self, offering_id: uuid.UUID, user: User) -> dict[str, Any]:
        (offering, course, semester), manager = await self._authorize_offering(offering_id, user)
        recent = await self.list_announcements(offering_id, user, limit=5, offset=0)
        resources = await self.list_resources(offering_id, user)
        enrollment_count = int(
            await self.db.scalar(
                select(func.count())
                .select_from(CourseEnrollment)
                .join(User, User.id == CourseEnrollment.student_id)
                .where(
                    CourseEnrollment.course_offering_id == offering_id,
                    CourseEnrollment.status.in_(ACTIVE_ENROLLMENT_STATUSES),
                    User.is_active.is_(True),
                )
            )
            or 0
        )
        return {
            "offering_id": offering.id,
            "offering_status": offering.publication_status,
            "course": {
                "id": course.id,
                "course_code": course.course_code,
                "title": course.title,
                "credit_hours": float(course.credit_hours),
                "type": course.type,
                "description": course.description,
            },
            "semester": {
                "id": semester.id,
                "title": semester.title,
                "target_term": semester.target_term,
                "is_active": bool(semester.is_active),
                "start_date": semester.start_date,
                "end_date": semester.end_date,
            },
            "authorized_teachers": await self._authorized_teachers(offering_id),
            "active_enrollment_count": enrollment_count,
            "unread_announcement_count": await self._visible_unread_count(offering_id, user, manager),
            "recent_activity": recent["items"],
            "upcoming_schedules": await self._schedules(offering_id),
            "resources": resources,
            "events": await self.list_events(offering_id, user),
            "questions": await self.list_questions(offering_id, user),
            "permissions": self._permissions(manager),
            **self._permissions(manager),
            "links": {
                "self": f"/course-offerings/{offering_id}/workspace",
                "announcements": f"/course-offerings/{offering_id}/announcements",
                "resources": f"/course-offerings/{offering_id}/resources",
                "attendance": (
                    f"/attendance/courses/{offering_id}/summary" if manager else "/attendance/my-summary"
                ),
            },
        }


__all__ = ["CourseWorkspaceService", "announcement_event_id"]
