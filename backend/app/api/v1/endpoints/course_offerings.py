"""Course-offering administration, teacher assignment and enrollment APIs."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import RequireRole, get_current_user, verify_course_teacher
from app.core.database import get_db
from app.core.exceptions import ForbiddenException
from app.models.user import User, UserRole
from app.schemas.academic import (
    ActiveCreditTotalResponse,
    AssignmentDecisionRequest,
    CourseOfferingCreate,
    CourseOfferingPublicationRequest,
    CourseOfferingResponse,
    CourseOfferingUpdate,
    EnrollmentCreate,
    EnrollmentResponse,
    RosterEntryResponse,
    SemesterResponse,
    TeacherCourseOfferingCreate,
    TeacherAssignmentRequestResponse,
)
from app.services.course_offering_service import CourseOfferingService

router = APIRouter(prefix="/course-offerings", tags=["Course Offerings"])

ADMIN = [UserRole.SUPER_ADMIN]
TEACHER = [UserRole.TEACHER]
STUDENT_OR_CR = [UserRole.STUDENT, UserRole.CR]


async def verify_offering_teacher(
    offering_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Adapt the shared dependency's parameter name to this route."""
    return await verify_course_teacher(offering_id, user, db)


@router.post("", response_model=CourseOfferingResponse, status_code=status.HTTP_201_CREATED)
async def create_course_offering(
    payload: CourseOfferingCreate,
    user: User = Depends(RequireRole(ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    return await CourseOfferingService(db).create_offering(user.id, payload.course_id, payload.semester_id)


@router.post("/provide", response_model=CourseOfferingResponse, status_code=status.HTTP_201_CREATED)
async def provide_course_offering(
    payload: TeacherCourseOfferingCreate,
    user: User = Depends(RequireRole(TEACHER)),
    db: AsyncSession = Depends(get_db),
):
    return await CourseOfferingService(db).provide_offering(
        user.id,
        course_code=payload.course_code,
        title=payload.title,
        credit_hours=payload.credit_hours,
        course_type=payload.course_type,
        semester_id=payload.semester_id,
        description=payload.description,
    )


@router.get("", response_model=list[CourseOfferingResponse])
async def list_course_offerings_for_role(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CourseOfferingService(db)
    if user.role == UserRole.TEACHER:
        return await service.list_available_offerings(user.id)
    if user.role in STUDENT_OR_CR:
        return await service.list_published_offerings(user.id)
    if user.role == UserRole.SUPER_ADMIN:
        return await service.list_available_offerings(user.id)
    raise ForbiddenException("This account cannot access course offerings.")


@router.patch("/{offering_id}", response_model=CourseOfferingResponse)
async def update_course_offering(
    offering_id: uuid.UUID,
    payload: CourseOfferingUpdate,
    user: User = Depends(RequireRole(ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    return await CourseOfferingService(db).update_offering(
        offering_id,
        course_id=payload.course_id,
        semester_id=payload.semester_id,
    )


async def _set_publication(
    offering_id: uuid.UUID,
    published: bool,
    user: User,
    db: AsyncSession,
):
    return await CourseOfferingService(db).set_publication(offering_id, user.id, published)


@router.patch("/{offering_id}/publication", response_model=CourseOfferingResponse)
async def set_course_offering_publication(
    offering_id: uuid.UUID,
    payload: CourseOfferingPublicationRequest,
    user: User = Depends(RequireRole(ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    return await _set_publication(offering_id, payload.published, user, db)


@router.post("/{offering_id}/publish", response_model=CourseOfferingResponse)
async def publish_course_offering(
    offering_id: uuid.UUID,
    user: User = Depends(RequireRole(ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    return await _set_publication(offering_id, True, user, db)


@router.post("/{offering_id}/unpublish", response_model=CourseOfferingResponse)
async def unpublish_course_offering(
    offering_id: uuid.UUID,
    user: User = Depends(RequireRole(ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    return await _set_publication(offering_id, False, user, db)


@router.get("/published", response_model=list[CourseOfferingResponse])
async def list_published_course_offerings(
    user: User = Depends(RequireRole(STUDENT_OR_CR)),
    db: AsyncSession = Depends(get_db),
):
    return await CourseOfferingService(db).list_published_offerings(user.id)


@router.get("/available", response_model=list[CourseOfferingResponse])
async def list_available_course_offerings(
    user: User = Depends(RequireRole(TEACHER)),
    db: AsyncSession = Depends(get_db),
):
    return await CourseOfferingService(db).list_available_offerings(user.id)


@router.get("/semesters/active", response_model=list[SemesterResponse])
async def list_active_semesters(
    user: User = Depends(RequireRole([*STUDENT_OR_CR, UserRole.SUPER_ADMIN, UserRole.TEACHER])),
    db: AsyncSession = Depends(get_db),
):
    student_id = user.id if user.role in STUDENT_OR_CR else None
    return await CourseOfferingService(db).list_active_semesters(student_id)


@router.get("/assignment-requests", response_model=list[TeacherAssignmentRequestResponse])
async def list_assignment_requests(
    request_status: str | None = Query(default=None, alias="status"),
    user: User = Depends(RequireRole(ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    return await CourseOfferingService(db).list_assignment_requests(status=request_status)


@router.get("/assignment-requests/mine", response_model=list[TeacherAssignmentRequestResponse])
async def list_my_assignment_requests(
    user: User = Depends(RequireRole(TEACHER)),
    db: AsyncSession = Depends(get_db),
):
    return await CourseOfferingService(db).list_assignment_requests(teacher_id=user.id)


@router.post(
    "/{offering_id}/assignment-requests",
    response_model=TeacherAssignmentRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def request_course_offering_assignment(
    offering_id: uuid.UUID,
    user: User = Depends(RequireRole(TEACHER)),
    db: AsyncSession = Depends(get_db),
):
    return await CourseOfferingService(db).request_assignment(offering_id, user.id)


@router.patch(
    "/assignment-requests/{request_id}",
    response_model=TeacherAssignmentRequestResponse,
)
async def decide_course_offering_assignment(
    request_id: uuid.UUID,
    payload: AssignmentDecisionRequest,
    user: User = Depends(RequireRole(ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    return await CourseOfferingService(db).decide_assignment(
        request_id,
        user.id,
        payload.decision,
        payload.rejection_reason,
    )


@router.get("/{offering_id}/roster", response_model=list[RosterEntryResponse])
async def get_course_roster(
    offering_id: uuid.UUID,
    user: User = Depends(verify_offering_teacher),
    db: AsyncSession = Depends(get_db),
):
    return await CourseOfferingService(db).roster(offering_id)


@router.get("/enrollments/me", response_model=list[EnrollmentResponse])
async def list_my_enrollments(
    user: User = Depends(RequireRole(STUDENT_OR_CR)),
    db: AsyncSession = Depends(get_db),
):
    return await CourseOfferingService(db).list_enrollments(user.id)


@router.get("/enrollments/me/credits", response_model=ActiveCreditTotalResponse)
async def get_my_active_credit_total(
    user: User = Depends(RequireRole(STUDENT_OR_CR)),
    db: AsyncSession = Depends(get_db),
):
    total = await CourseOfferingService(db).active_credit_total(user.id)
    return {"active_credit_total": float(total)}


@router.post(
    "/{offering_id}/enroll",
    response_model=EnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def enroll_in_course_offering(
    offering_id: uuid.UUID,
    payload: EnrollmentCreate | None = None,
    user: User = Depends(RequireRole(STUDENT_OR_CR)),
    db: AsyncSession = Depends(get_db),
):
    enrollment_type = payload.enrollment_type if payload else "enrolled"
    enrollment = await CourseOfferingService(db).enroll(user.id, offering_id, enrollment_type)
    rows = await CourseOfferingService(db).list_enrollments(user.id)
    return next(row for row in rows if row["id"] == enrollment.id)


@router.post("/enrollments/{enrollment_id}/drop", response_model=EnrollmentResponse)
async def drop_my_enrollment(
    enrollment_id: int,
    user: User = Depends(RequireRole(STUDENT_OR_CR)),
    db: AsyncSession = Depends(get_db),
):
    enrollment = await CourseOfferingService(db).drop(enrollment_id, user.id)
    rows = await CourseOfferingService(db).list_enrollments(user.id)
    return next(row for row in rows if row["id"] == enrollment.id)


@router.post("/enrollments/{enrollment_id}/reselect", response_model=EnrollmentResponse)
async def reselect_my_enrollment(
    enrollment_id: int,
    payload: EnrollmentCreate | None = None,
    user: User = Depends(RequireRole(STUDENT_OR_CR)),
    db: AsyncSession = Depends(get_db),
):
    enrollment_type = payload.enrollment_type if payload else "enrolled"
    enrollment = await CourseOfferingService(db).reselect(enrollment_id, user.id, enrollment_type)
    rows = await CourseOfferingService(db).list_enrollments(user.id)
    return next(row for row in rows if row["id"] == enrollment.id)
