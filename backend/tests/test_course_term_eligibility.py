"""Same-term-or-senior policy at the offering API and transaction boundaries."""

import uuid
from datetime import date

import pytest
from sqlalchemy import func, select

from app.models.academic import Course, CourseEnrollment, CourseOffering, CourseOfferingTeacher, Semester
from app.models.notification import Notification, NotificationLog
from app.models.user import StudentProfile, User, UserRole
from tests.conftest import auth_header, make_user
from tests.test_course_offerings import make_offering

pytestmark = pytest.mark.asyncio

# Expected order is specified independently of the implementation under test.
TERMS = ("1-1", "1-2", "2-1", "2-2", "3-1", "3-2", "4-1", "4-2")


async def student_at(db, term, *, role=UserRole.STUDENT, active=True):
    student = await make_user(db, role=role, is_active=active)
    if term is not None:
        db.add(StudentProfile(user_id=student.id, session_year="2023-2024", current_term=term))
        await db.commit()
    return student


@pytest.mark.parametrize("role", [UserRole.STUDENT, UserRole.CR])
@pytest.mark.parametrize("current_term", [*TERMS, None, "", "9-9", "3-9", "3-1 ", "3.1"])
async def test_lists_and_guessed_enrollment_ids_share_term_policy(client, db, role, current_term):
    student = await student_at(db, current_term, role=role)
    scoped = [await make_offering(db, target_term=term, credits=1.5) for term in TERMS]
    legacy, _, legacy_semester = await make_offering(db, credits=1.5)
    draft, _, draft_semester = await make_offering(db, target_term="1-1", published=False)
    inactive, _, _ = await make_offering(db, target_term="1-1", active=False)
    eligible_count = TERMS.index(current_term) + 1 if current_term in TERMS else 0
    expected_offerings = {str(legacy.id), *(str(row[0].id) for row in scoped[:eligible_count])}

    for path in ("/api/v1/course-offerings", "/api/v1/course-offerings/published"):
        listing = await client.get(path, headers=auth_header(student))
        assert listing.status_code == 200, listing.text
        assert {row["id"] for row in listing.json()} == expected_offerings

    semesters = await client.get("/api/v1/course-offerings/semesters/active", headers=auth_header(student))
    assert semesters.status_code == 200, semesters.text
    expected_semesters = {legacy_semester.id, *(row[2].id for row in scoped[:eligible_count])}
    if eligible_count:
        expected_semesters.add(draft_semester.id)  # semester visibility does not require a published course
    assert {row["id"] for row in semesters.json()} == expected_semesters

    assert await db.scalar(select(func.count()).select_from(CourseEnrollment)) == 0
    for index, (offering, _, _) in enumerate(scoped):
        result = await client.post(f"/api/v1/course-offerings/{offering.id}/enroll", headers=auth_header(student))
        assert result.status_code == (201 if index < eligible_count else 403), result.text
    for offering in (draft, inactive):
        result = await client.post(f"/api/v1/course-offerings/{offering.id}/enroll", headers=auth_header(student))
        assert result.status_code == 409, result.text
    result = await client.post(f"/api/v1/course-offerings/{legacy.id}/enroll", headers=auth_header(student))
    assert result.status_code == 201, result.text
    enrolled_ids = (await db.scalars(select(CourseEnrollment.course_offering_id))).all()
    assert {str(offering_id) for offering_id in enrolled_ids} == expected_offerings
    assert await db.scalar(select(func.count()).select_from(NotificationLog)) == eligible_count + 1


async def test_scoped_creation_and_assignment_notify_exact_active_same_or_senior_recipients(client, db):
    admin = await make_user(db, role=UserRole.SUPER_ADMIN)
    teacher = await make_user(db, role=UserRole.TEACHER)
    colleague = await make_user(db, role=UserRole.TEACHER)
    students = [await student_at(db, term, role=role) for role in (UserRole.STUDENT, UserRole.CR)
                for term in TERMS]
    expected = {student.id for student in students[4:8] + students[12:16]}
    for role in (UserRole.STUDENT, UserRole.CR):
        for term in (None, "", "9-9", "3-9", "3-1 "):
            await student_at(db, term, role=role)
        await student_at(db, "3-1", role=role, active=False)
        await student_at(db, "4-2", role=role, active=False)
    for role in (UserRole.SUPER_ADMIN, UserRole.TEACHER, UserRole.LAB_ASSISTANT, UserRole.ALUMNI):
        await student_at(db, "4-2", role=role)

    semester = Semester(title="Scoped notifications", target_term="3-1", is_active=True,
                        start_date=date(2030, 1, 1), end_date=date(2030, 6, 30))
    db.add(semester)
    await db.commit()
    provided = await client.post("/api/v1/course-offerings/provide", headers=auth_header(teacher), json={
        "course_code": "EEE 501", "title": "Term policy", "credit_hours": 3,
        "course_type": "theory", "semester_id": semester.id,
    })
    assert provided.status_code == 201, provided.text
    offering = provided.json()
    assert offering["publication_status"] == "published"
    assert offering["created_by"] == str(teacher.id)
    assert offering["assigned_teachers"] == [{
        "teacher_id": str(teacher.id), "teacher_name": teacher.full_name, "role": "course_teacher",
    }]
    assert await db.scalar(select(func.count()).select_from(CourseEnrollment)) == 0
    recipients = (await db.scalars(select(NotificationLog.user_id).where(NotificationLog.type == "course_available"))).all()
    assert len(recipients) == len(expected)
    assert set(recipients) == expected
    assert set((await db.scalars(select(Notification.recipient_id))).all()) == expected

    requested = await client.post(
        f"/api/v1/course-offerings/{offering['id']}/assignment-requests", headers=auth_header(colleague),
    )
    assert requested.status_code == 201, requested.text
    approved = await client.patch(
        f"/api/v1/course-offerings/assignment-requests/{requested.json()['id']}",
        headers=auth_header(admin), json={"decision": "approve"},
    )
    assert approved.status_code == 200, approved.text
    recipients = (await db.scalars(select(NotificationLog.user_id).where(NotificationLog.type == "course_assignment"))).all()
    assert len(recipients) == len(expected)
    assert set(recipients) == expected
    assert await db.scalar(select(func.count()).select_from(Notification)) == 2 * len(expected)
    assert await db.scalar(select(func.count()).select_from(CourseEnrollment)) == 0


@pytest.mark.parametrize("role", [role for role in UserRole if role != UserRole.TEACHER])
async def test_provide_remains_teacher_only_including_admin(client, db, role):
    user = await make_user(db, role=role)
    _, _, semester = await make_offering(db, target_term="1-1")
    response = await client.post("/api/v1/course-offerings/provide", headers=auth_header(user), json={
        "course_code": "EEE 502", "title": "Not a teacher", "credit_hours": 3,
        "course_type": "theory", "semester_id": semester.id,
    })
    assert response.status_code == 403, response.text
    assert await db.scalar(select(Course.id).where(Course.course_code == "EEE 502")) is None
    assert await db.scalar(select(func.count()).select_from(CourseOffering)) == 1
    for model in (CourseOfferingTeacher, CourseEnrollment, NotificationLog, Notification):
        assert await db.scalar(select(func.count()).select_from(model)) == 0


@pytest.mark.parametrize("active,target_term", [(False, "1-1"), (True, None)])
async def test_provide_still_requires_active_scoped_semester(client, db, active, target_term):
    teacher = await make_user(db, role=UserRole.TEACHER)
    _, _, semester = await make_offering(db, active=active, target_term=target_term)
    response = await client.post("/api/v1/course-offerings/provide", headers=auth_header(teacher), json={
        "course_code": "EEE 503", "title": "Unavailable semester", "credit_hours": 3,
        "course_type": "theory", "semester_id": semester.id,
    })
    assert response.status_code == 422, response.text
    assert await db.scalar(select(Course.id).where(Course.course_code == "EEE 503")) is None
    assert await db.scalar(select(func.count()).select_from(CourseEnrollment)) == 0
    assert await db.scalar(select(func.count()).select_from(NotificationLog)) == 0


@pytest.mark.parametrize("path", ["reselect", "enroll"])
@pytest.mark.parametrize("current_term", ["3-1", "3-2", "4-2", "2-2", None, "9-9", "3-9"])
async def test_reselection_checks_current_profile_and_preserves_dropped_row_on_rejection(client, db, path, current_term):
    student = await student_at(db, "3-1")
    offering, _, _ = await make_offering(db, target_term="3-1")
    selected = await client.post(f"/api/v1/course-offerings/{offering.id}/enroll", headers=auth_header(student))
    assert selected.status_code == 201, selected.text
    enrollment_id = selected.json()["id"]
    dropped = await client.post(
        f"/api/v1/course-offerings/enrollments/{enrollment_id}/drop", headers=auth_header(student),
    )
    assert dropped.status_code == 200
    profile = await db.get(StudentProfile, student.id)
    if current_term is None:
        await db.delete(profile)
    else:
        profile.current_term = current_term
    await db.commit()
    # Read persisted timestamps before comparing: SQLite strips their UTC suffix.
    before = (await client.get(
        "/api/v1/course-offerings/enrollments/me", headers=auth_header(student),
    )).json()[0]
    endpoint = (f"/api/v1/course-offerings/enrollments/{enrollment_id}/reselect" if path == "reselect"
                else f"/api/v1/course-offerings/{offering.id}/enroll")
    result = await client.post(endpoint, headers=auth_header(student), json={"enrollment_type": "improvement"})
    eligible = current_term in ("3-1", "3-2", "4-2")
    assert result.status_code == ((200 if path == "reselect" else 201) if eligible else 403), result.text
    history = await client.get("/api/v1/course-offerings/enrollments/me", headers=auth_header(student))
    assert len(history.json()) == 1
    row = history.json()[0]
    assert row["id"] == enrollment_id
    if eligible:
        assert row["status"] == "improvement"
        assert row["dropped_at"] is None
    else:
        assert row == before
    credits = await client.get("/api/v1/course-offerings/enrollments/me/credits", headers=auth_header(student))
    assert credits.json() == {"active_credit_total": 3.0 if eligible else 0.0}
    assert await db.scalar(select(func.count()).select_from(NotificationLog)) == (2 if eligible else 1)


@pytest.mark.parametrize("current_term", ["3-1", "3-2", "4-2", "2-2"])
async def test_registration_checks_all_terms_and_rolls_back_account_and_selections(client, db, current_term):
    # 15 credits across older and same-term courses. One guessed senior-only
    # selection must reject the entire registration, including eligible courses.
    offerings = [(await make_offering(db, target_term=term))[0]
                 for term in ("1-1", "1-2", "2-1", "2-2", "3-1")]
    identifier = f"term-{uuid.uuid4().hex[:12]}"
    response = await client.post("/api/v1/auth/register/student", json={
        "full_name": "Term Registration", "identifier": identifier,
        "email": f"{identifier}@sust.edu", "password": "Passw0rd!23",
        "session_year": "2023-2024", "current_term": current_term,
        "course_selections": [{"course_offering_id": str(offering.id)} for offering in offerings],
    })
    eligible = current_term != "2-2"
    assert response.status_code == (201 if eligible else 422), response.text
    user = await db.scalar(select(User).where(User.identifier == identifier))
    if eligible:
        assert user is not None
        assert (await db.get(StudentProfile, user.id)).current_term == current_term
        history = await client.get("/api/v1/course-offerings/enrollments/me", headers=auth_header(user))
        assert {row["course_offering_id"] for row in history.json()} == {str(offering.id) for offering in offerings}
        credits = await client.get("/api/v1/course-offerings/enrollments/me/credits", headers=auth_header(user))
        assert credits.json() == {"active_credit_total": 15.0}
    else:
        assert user is None
        assert await db.scalar(select(func.count()).select_from(StudentProfile)) == 0
    for model in (CourseEnrollment, NotificationLog, Notification):
        assert await db.scalar(select(func.count()).select_from(model)) == (5 if eligible else 0)


@pytest.mark.parametrize("course_count,expected_status", [(0, 201), (4, 422), (5, 201), (8, 201), (9, 422)])
async def test_senior_registration_retains_credit_boundaries(client, db, course_count, expected_status):
    offerings = [(await make_offering(db, target_term="2-2"))[0] for _ in range(course_count)]
    identifier = f"credits-{uuid.uuid4().hex[:12]}"
    response = await client.post("/api/v1/auth/register/student", json={
        "full_name": "Senior Credits", "identifier": identifier,
        "email": f"{identifier}@sust.edu", "password": "Passw0rd!23",
        "session_year": "2023-2024", "current_term": "3-1",
        "course_selections": [{"course_offering_id": str(offering.id)} for offering in offerings],
    })
    assert response.status_code == expected_status, response.text
    assert await db.scalar(select(func.count()).select_from(CourseEnrollment)) == (
        course_count if expected_status == 201 else 0
    )
    if expected_status == 422:
        assert await db.scalar(select(User.id).where(User.identifier == identifier)) is None
        assert await db.scalar(select(func.count()).select_from(StudentProfile)) == 0
        assert await db.scalar(select(func.count()).select_from(NotificationLog)) == 0
