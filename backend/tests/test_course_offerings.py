"""API contracts for offering administration, assignment and enrollment."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ResourceConflictException
from app.models.academic import (
    Course,
    CourseEnrollment,
    CourseOffering,
    CourseOfferingTeacher,
    Semester,
    TeacherAssignmentRequest,
)
from app.models.user import User, UserRole
from app.services.course_offering_service import CourseOfferingService
from tests.conftest import auth_header, make_user

pytestmark = pytest.mark.asyncio


async def make_offering(db, *, admin=None, active=True, published=True, credits=3.0):
    suffix = uuid.uuid4().hex[:8]
    semester = Semester(
        title=f"Term {suffix}",
        is_active=active,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    course = Course(
        course_code=f"T{suffix}",
        title="API test course",
        credit_hours=Decimal(str(credits)),
        type="theory",
        description="fixture",
    )
    db.add_all([semester, course])
    await db.flush()
    offering = CourseOffering(
        course_id=course.id,
        semester_id=semester.id,
        created_by=admin.id if admin else None,
        publication_status="published" if published else "draft",
    )
    db.add(offering)
    await db.commit()
    await db.refresh(offering)
    return offering, course, semester


async def test_admin_offering_lifecycle_and_role_permissions(client, db):
    admin = await make_user(db, role=UserRole.SUPER_ADMIN)
    student = await make_user(db, role=UserRole.STUDENT)
    offering, _, semester = await make_offering(db, admin=admin, published=False)
    _, replacement_course, _ = await make_offering(
        db, admin=admin, published=False, credits=1.5
    )

    denied = await client.post(
        "/api/v1/course-offerings",
        json={"course_id": str(replacement_course.id), "semester_id": semester.id},
        headers=auth_header(student),
    )
    assert denied.status_code == 403

    updated = await client.patch(
        f"/api/v1/course-offerings/{offering.id}",
        json={
            "course_id": str(replacement_course.id),
            "semester_id": semester.id,
        },
        headers=auth_header(admin),
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["id"] == str(offering.id)
    assert updated.json()["credit_hours"] == 1.5

    created = await client.post(
        "/api/v1/course-offerings",
        json={"course_id": str(replacement_course.id), "semester_id": semester.id},
        headers=auth_header(admin),
    )
    assert created.status_code == 409  # the course/semester pair already exists

    published = await client.post(
        f"/api/v1/course-offerings/{offering.id}/publish",
        headers=auth_header(admin),
    )
    assert published.status_code == 200, published.text
    assert published.json()["publication_status"] == "published"
    assert published.json()["credit_hours"] == 1.5
    assert published.json()["created_by"] == str(admin.id)

    unpublished = await client.post(
        f"/api/v1/course-offerings/{offering.id}/unpublish",
        headers=auth_header(admin),
    )
    assert unpublished.status_code == 200
    assert unpublished.json()["publication_status"] == "draft"


async def test_admin_can_read_active_semesters_for_offering_management(client, db):
    admin = await make_user(db, role=UserRole.SUPER_ADMIN)
    await make_offering(db, admin=admin, active=True, published=False)

    response = await client.get(
        "/api/v1/course-offerings/semesters/active", headers=auth_header(admin)
    )

    assert response.status_code == 200, response.text
    assert response.json()
    assert all(row["is_active"] for row in response.json())


@pytest.mark.parametrize("role", [UserRole.STUDENT, UserRole.CR])
async def test_students_see_only_published_active_offerings_and_enroll(client, db, role):
    student = await make_user(db, role=role)
    draft, _, _ = await make_offering(db, published=False)
    inactive, _, _ = await make_offering(db, active=False, published=True)
    published, course, semester = await make_offering(db, published=True, credits=1.5)

    listing = await client.get("/api/v1/course-offerings/published", headers=auth_header(student))
    assert listing.status_code == 200
    assert {row["id"] for row in listing.json()} == {str(published.id)}
    active_semesters = await client.get(
        "/api/v1/course-offerings/semesters/active", headers=auth_header(student)
    )
    assert active_semesters.status_code == 200
    assert all(row["is_active"] for row in active_semesters.json())
    assert listing.json()[0]["semester_is_active"] is True

    draft_result = await client.post(
        f"/api/v1/course-offerings/{draft.id}/enroll", headers=auth_header(student)
    )
    inactive_result = await client.post(
        f"/api/v1/course-offerings/{inactive.id}/enroll", headers=auth_header(student)
    )
    assert draft_result.status_code == inactive_result.status_code == 409

    enrolled = await client.post(
        f"/api/v1/course-offerings/{published.id}/enroll",
        json={"enrollment_type": "main", "credit_hours": 99},
        headers=auth_header(student),
    )
    assert enrolled.status_code == 201, enrolled.text
    assert enrolled.json()["credit_hours"] == 1.5
    assert enrolled.json()["semester_id"] == semester.id
    assert enrolled.json()["course_code"] == course.course_code

    duplicate = await client.post(
        f"/api/v1/course-offerings/{published.id}/enroll", headers=auth_header(student)
    )
    assert duplicate.status_code == 409
    assert await db.scalar(select(func.count()).select_from(CourseEnrollment)) == 1


async def test_drop_reselect_ownership_and_active_credits(client, db):
    student = await make_user(db, role=UserRole.STUDENT)
    other = await make_user(db, role=UserRole.STUDENT)
    offering, course, _ = await make_offering(db, published=True, credits=3.0)

    enrolled = await client.post(
        f"/api/v1/course-offerings/{offering.id}/enroll", headers=auth_header(student)
    )
    enrollment_id = enrolled.json()["id"]
    assert enrolled.status_code == 201

    forbidden = await client.post(
        f"/api/v1/course-offerings/enrollments/{enrollment_id}/drop",
        headers=auth_header(other),
    )
    assert forbidden.status_code == 403

    dropped = await client.post(
        f"/api/v1/course-offerings/enrollments/{enrollment_id}/drop",
        headers=auth_header(student),
    )
    assert dropped.status_code == 200
    assert dropped.json()["status"] == "drop"
    assert dropped.json()["dropped_at"] is not None
    assert datetime.fromisoformat(dropped.json()["enrolled_at"]).replace(tzinfo=None) == (
        datetime.fromisoformat(enrolled.json()["enrolled_at"]).replace(tzinfo=None)
    )  # SQLite reads timestamps without the UTC timezone suffix.

    duplicate_drop = await client.post(
        f"/api/v1/course-offerings/enrollments/{enrollment_id}/drop", headers=auth_header(student),
    )
    assert duplicate_drop.status_code == 409
    forbidden_reselect = await client.post(
        f"/api/v1/course-offerings/enrollments/{enrollment_id}/reselect", headers=auth_header(other),
    )
    assert forbidden_reselect.status_code == 403

    credits_after_drop = await client.get(
        "/api/v1/course-offerings/enrollments/me/credits", headers=auth_header(student)
    )
    assert credits_after_drop.json() == {"active_credit_total": 0.0}

    reselected = await client.post(
        f"/api/v1/course-offerings/enrollments/{enrollment_id}/reselect",
        json={"enrollment_type": "improvement"},
        headers=auth_header(student),
    )
    assert reselected.status_code == 200
    assert reselected.json()["id"] == enrollment_id
    assert reselected.json()["status"] == "improvement"
    assert reselected.json()["credit_hours"] == 3.0
    assert reselected.json()["dropped_at"] is None
    assert datetime.fromisoformat(reselected.json()["enrolled_at"]).replace(tzinfo=None) == (
        datetime.fromisoformat(enrolled.json()["enrolled_at"]).replace(tzinfo=None)
    )
    assert await db.scalar(select(func.count()).select_from(CourseEnrollment)) == 1

    duplicate_reselect = await client.post(
        f"/api/v1/course-offerings/enrollments/{enrollment_id}/reselect", headers=auth_header(student),
    )
    assert duplicate_reselect.status_code == 409

    credits = await client.get(
        "/api/v1/course-offerings/enrollments/me/credits", headers=auth_header(student)
    )
    assert credits.json() == {"active_credit_total": 3.0}

    # The only credit source is the catalogue row, not the enrollment payload.
    course.credit_hours = Decimal("4.5")
    await db.commit()
    changed_credits = await client.get(
        "/api/v1/course-offerings/enrollments/me/credits", headers=auth_header(student)
    )
    assert changed_credits.json() == {"active_credit_total": 4.5}


@pytest.mark.parametrize("unavailable", ["draft", "inactive"])
async def test_reselect_requires_current_published_active_offering(client, db, unavailable):
    student = await make_user(db)
    offering, _, semester = await make_offering(db)
    response = await client.post(f"/api/v1/course-offerings/{offering.id}/enroll", headers=auth_header(student))
    enrollment_id = response.json()["id"]
    await client.post(f"/api/v1/course-offerings/enrollments/{enrollment_id}/drop", headers=auth_header(student))
    if unavailable == "draft":
        offering.publication_status = "draft"
    else:
        semester.is_active = False
    await db.commit()

    response = await client.post(
        f"/api/v1/course-offerings/enrollments/{enrollment_id}/reselect", headers=auth_header(student),
    )
    assert response.status_code == 409
    persisted = (await client.get("/api/v1/course-offerings/enrollments/me", headers=auth_header(student))).json()
    assert len(persisted) == 1
    assert persisted[0]["id"] == enrollment_id
    assert persisted[0]["status"] == "drop"


async def test_teacher_request_approval_controls_roster_access(client, db):
    admin = await make_user(db, role=UserRole.SUPER_ADMIN)
    teacher = await make_user(db, role=UserRole.TEACHER)
    other_teacher = await make_user(db, role=UserRole.TEACHER)
    student = await make_user(db, role=UserRole.STUDENT)
    offering, _, _ = await make_offering(db, admin=admin, published=True)

    request = await client.post(
        f"/api/v1/course-offerings/{offering.id}/assignment-requests",
        headers=auth_header(teacher),
    )
    assert request.status_code == 201, request.text
    request_id = request.json()["id"]
    duplicate = await client.post(
        f"/api/v1/course-offerings/{offering.id}/assignment-requests",
        headers=auth_header(teacher),
    )
    assert duplicate.status_code == 409

    before = await client.get(
        "/api/v1/course-offerings/assignment-requests/mine", headers=auth_header(teacher)
    )
    assert before.status_code == 200
    assert before.json()[0]["status"] == "pending"

    denied = await client.patch(
        f"/api/v1/course-offerings/assignment-requests/{request_id}",
        json={"decision": "approve"},
        headers=auth_header(teacher),
    )
    assert denied.status_code == 403

    approved = await client.patch(
        f"/api/v1/course-offerings/assignment-requests/{request_id}",
        json={"decision": "approve"},
        headers=auth_header(admin),
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    published_listing = await client.get(
        "/api/v1/course-offerings/published", headers=auth_header(student)
    )
    assert published_listing.status_code == 200
    assert published_listing.json()[0]["assigned_teachers"] == [{
        "teacher_id": str(teacher.id),
        "teacher_name": teacher.full_name,
        "role": "course_teacher",
    }]

    enrolled = await client.post(
        f"/api/v1/course-offerings/{offering.id}/enroll", headers=auth_header(student)
    )
    assert enrolled.status_code == 201

    dropped_student = await make_user(db, role=UserRole.STUDENT)
    dropped = await client.post(
        f"/api/v1/course-offerings/{offering.id}/enroll", headers=auth_header(dropped_student)
    )
    assert dropped.status_code == 201
    dropped_result = await client.post(
        f"/api/v1/course-offerings/enrollments/{dropped.json()['id']}/drop",
        headers=auth_header(dropped_student),
    )
    assert dropped_result.status_code == 200

    roster = await client.get(
        f"/api/v1/course-offerings/{offering.id}/roster", headers=auth_header(teacher)
    )
    assert roster.status_code == 200, roster.text
    assert [row["student_id"] for row in roster.json()] == [str(student.id)]

    not_approved = await client.get(
        f"/api/v1/course-offerings/{offering.id}/roster", headers=auth_header(other_teacher)
    )
    assert not_approved.status_code == 403

    rejected_request = await client.post(
        f"/api/v1/course-offerings/{offering.id}/assignment-requests",
        headers=auth_header(other_teacher),
    )
    assert rejected_request.status_code == 201
    rejected = await client.patch(
        f"/api/v1/course-offerings/assignment-requests/{rejected_request.json()['id']}",
        json={"decision": "reject", "rejection_reason": "Schedule conflict."},
        headers=auth_header(admin),
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["rejection_reason"] == "Schedule conflict."

    assignment = await db.scalar(
        select(CourseOfferingTeacher).where(
            CourseOfferingTeacher.course_offering_id == offering.id,
            CourseOfferingTeacher.teacher_id == teacher.id,
        )
    )
    assert assignment is not None


async def test_assignment_approval_rolls_back_request_and_assignment_together(db):
    admin = await make_user(db, role=UserRole.SUPER_ADMIN)
    teacher = await make_user(db, role=UserRole.TEACHER)
    offering, _, _ = await make_offering(db, admin=admin, published=True)
    offering_id = offering.id
    teacher_id = teacher.id
    request = TeacherAssignmentRequest(
        course_offering_id=offering.id,
        teacher_id=teacher.id,
        status="pending",
    )
    db.add(request)
    await db.commit()
    await db.refresh(request)
    request_id = request.id

    service = CourseOfferingService(db)

    async def fail_after_mutation(commit):
        raise IntegrityError("forced rollback", {}, RuntimeError("test"))

    original_finish = service._finish
    service._finish = fail_after_mutation
    with pytest.raises(ResourceConflictException):
        await service.decide_assignment(request_id, admin.id, "approve")
    service._finish = original_finish

    persisted = await db.get(TeacherAssignmentRequest, request_id)
    assert persisted.status == "pending"
    assert await db.scalar(
        select(CourseOfferingTeacher).where(
            CourseOfferingTeacher.course_offering_id == offering_id,
            CourseOfferingTeacher.teacher_id == teacher_id,
        )
    ) is None


@pytest.mark.parametrize("request_status", [None, "pending", "approved", "rejected"])
async def test_roster_checks_decision_on_existing_teacher_assignment(client, db, request_status):
    teacher = await make_user(db, role=UserRole.TEACHER)
    student = await make_user(db)
    offering, _, _ = await make_offering(db)
    db.add(CourseOfferingTeacher(course_offering_id=offering.id, teacher_id=teacher.id))
    db.add(CourseEnrollment(course_offering_id=offering.id, student_id=student.id))
    if request_status is not None:
        db.add(TeacherAssignmentRequest(
            course_offering_id=offering.id, teacher_id=teacher.id, status=request_status,
        ))
    await db.commit()

    response = await client.get(
        f"/api/v1/course-offerings/{offering.id}/roster", headers=auth_header(teacher),
    )
    # A legacy explicit assignment remains a grant; a pending/rejected request
    # must never override the approval boundary merely because a link exists.
    if request_status in ("pending", "rejected"):
        assert response.status_code == 403
    else:
        assert response.status_code == 200, response.text
        assert [row["student_id"] for row in response.json()] == [str(student.id)]


async def test_registration_selection_rollback_uses_enrollment_service(client, db):
    offering, _, _ = await make_offering(db, published=True)
    identifier = f"rollback-{uuid.uuid4().hex[:8]}"
    response = await client.post(
        "/api/v1/auth/register/student",
        json={
            "full_name": "Atomic Registration",
            "identifier": identifier,
            "email": f"{identifier}@sust.edu",
            "password": "Passw0rd!23",
            "session_year": "22-26",
            "current_term": "3-1",
            "course_selections": [
                {"course_offering_id": str(offering.id)},
                {"course_offering_id": str(uuid.uuid4())},
            ],
        },
    )
    assert response.status_code == 422
    assert await db.scalar(select(func.count()).select_from(CourseEnrollment)) == 0
    assert await db.scalar(select(User.id).where(User.identifier == identifier)) is None
