"""Eligibility through real API transactions and the migrated PostgreSQL schema."""

import uuid

import pytest

pytestmark = pytest.mark.asyncio


async def student_at(database, term, *, role="student", active=True):
    user = await database.user(role, active=active)
    if term is not None:
        await database.conn.execute(
            "INSERT INTO profiles_student(user_id,session_year,current_term) VALUES ($1,'2023-2024',$2)",
            user.id, term,
        )
    return user


async def scoped_semester(database, term):
    semester = await database.semester()
    await database.conn.execute("UPDATE semesters SET target_term=$1 WHERE id=$2", term, semester)
    return semester


async def test_teacher_provided_course_has_same_or_senior_visibility_and_exact_notification_recipients(api, database):
    teacher = await database.user("teacher")
    colleague = await database.user("teacher")
    admin = await database.user("super_admin")
    eligible = [await student_at(database, term, role=role)
                for role in ("student", "cr") for term in ("3-1", "3-2", "4-2")]
    ineligible = [await student_at(database, term, role=role)
                  for role in ("student", "cr") for term in ("1-1", "2-2", None, "9-9", "3-9", "3-1 ")]
    inactive = [await student_at(database, "4-2", role=role, active=False) for role in ("student", "cr")]
    for role in ("teacher", "super_admin", "alumni", "lab_assistant"):
        await student_at(database, "4-2", role=role)
    semester = await scoped_semester(database, "3-1")
    response = await api.post("/api/v1/course-offerings/provide", headers=database.headers(teacher), json={
        "course_code": "EEE 501", "title": "Advanced course", "credit_hours": 3,
        "course_type": "theory", "semester_id": semester,
    })
    assert response.status_code == 201, response.text
    provided = response.json()
    offering = uuid.UUID(provided["id"])
    assert provided["target_term"] == "3-1"
    assert provided["publication_status"] == "published"
    assert provided["created_by"] == str(teacher.id)
    assert provided["assigned_teachers"] == [{
        "teacher_id": str(teacher.id), "teacher_name": teacher.full_name, "role": "course_teacher",
    }]
    assert await database.conn.fetchval("SELECT count(*) FROM course_enrollments") == 0
    recipients = await database.conn.fetch("SELECT user_id FROM notification_log WHERE type='course_available'")
    assert len(recipients) == len(eligible)
    assert {row["user_id"] for row in recipients} == {user.id for user in eligible}
    inbox = await database.conn.fetch("SELECT recipient_id FROM notifications")
    assert {row["recipient_id"] for row in inbox} == {user.id for user in eligible}

    requested = await api.post(
        f"/api/v1/course-offerings/{offering}/assignment-requests", headers=database.headers(colleague),
    )
    assert requested.status_code == 201, requested.text
    approved = await api.patch(
        f"/api/v1/course-offerings/assignment-requests/{requested.json()['id']}",
        json={"decision": "approve"}, headers=database.headers(admin),
    )
    assert approved.status_code == 200, approved.text
    recipients = await database.conn.fetch("SELECT user_id FROM notification_log WHERE type='course_assignment'")
    assert len(recipients) == len(eligible)
    assert {row["user_id"] for row in recipients} == {user.id for user in eligible}
    assert await database.conn.fetchval("SELECT count(*) FROM notifications") == 2 * len(eligible)
    assert await database.conn.fetchval("SELECT count(*) FROM course_enrollments") == 0

    legacy_semester = await database.semester()
    legacy = await database.offering(semester=legacy_semester, published=True)
    draft = await database.offering(semester=semester)
    inactive_semester = await scoped_semester(database, "1-1")
    await database.conn.execute("UPDATE semesters SET is_active=false WHERE id=$1", inactive_semester)
    inactive_offering = await database.offering(semester=inactive_semester, published=True)
    for user in eligible + ineligible:
        expected = {str(legacy), str(offering)} if user in eligible else {str(legacy)}
        for path in ("/api/v1/course-offerings", "/api/v1/course-offerings/published"):
            listing = await api.get(path, headers=database.headers(user))
            assert listing.status_code == 200, listing.text
            assert {row["id"] for row in listing.json()} == expected
        semesters = await api.get("/api/v1/course-offerings/semesters/active", headers=database.headers(user))
        assert semesters.status_code == 200, semesters.text
        assert {row["id"] for row in semesters.json()} == (
            {semester, legacy_semester} if user in eligible else {legacy_semester}
        )
        enrolled = await api.post(f"/api/v1/course-offerings/{offering}/enroll", headers=database.headers(user))
        assert enrolled.status_code == (201 if user in eligible else 403), enrolled.text
        legacy_result = await api.post(f"/api/v1/course-offerings/{legacy}/enroll", headers=database.headers(user))
        assert legacy_result.status_code == 201, legacy_result.text
    for user in inactive:
        for path in ("/api/v1/course-offerings", "/api/v1/course-offerings/published",
                     "/api/v1/course-offerings/semesters/active"):
            denied = await api.get(path, headers=database.headers(user))
            assert denied.status_code == 401
        denied = await api.post(f"/api/v1/course-offerings/{offering}/enroll", headers=database.headers(user))
        assert denied.status_code == 401
    for unavailable in (draft, inactive_offering):
        denied = await api.post(
            f"/api/v1/course-offerings/{unavailable}/enroll", headers=database.headers(eligible[-1]),
        )
        assert denied.status_code == 409, denied.text
    persisted = await database.conn.fetch(
        "SELECT student_id FROM course_enrollments WHERE course_offering_id=$1", offering,
    )
    assert {row["student_id"] for row in persisted} == {user.id for user in eligible}


@pytest.mark.parametrize("current_term,expected_status", [("2-2", 201), ("3-1", 201), ("2-1", 422)])
async def test_registration_same_or_senior_policy_and_junior_atomic_rollback(api, database, current_term, expected_status):
    offerings = [await database.offering(semester=await scoped_semester(database, term), published=True)
                 for term in (None, "1-1", "1-2", "2-1", "2-2")]
    payload = {**database.registration(offerings), "current_term": current_term}
    result = await api.post("/api/v1/auth/register/student", json=payload)
    assert result.status_code == expected_status, result.text
    if expected_status == 422:
        for table in ("users", "profiles_student", "course_enrollments", "notification_log",
                      "notifications", "notification_batches", "notification_deliveries"):
            assert await database.conn.fetchval(f"SELECT count(*) FROM {table}") == 0
    else:
        profile = await database.conn.fetchrow("SELECT user_id,current_term FROM profiles_student")
        assert profile["current_term"] == current_term
        rows = await database.conn.fetch("SELECT student_id,course_offering_id,status FROM course_enrollments")
        assert {row["course_offering_id"] for row in rows} == set(offerings)
        assert all(row["student_id"] == profile["user_id"] and row["status"] == "main" for row in rows)
        assert await database.conn.fetchval("SELECT count(*) FROM notification_log") == 5


@pytest.mark.parametrize("path", ["reselect", "enroll"])
@pytest.mark.parametrize("current_term", ["3-1", "2-1", "9-9", None])
async def test_reselection_senior_eligibility_and_junior_rollback(api, database, path, current_term):
    student = await student_at(database, "2-2")
    offering = await database.offering(semester=await scoped_semester(database, "2-2"), published=True)
    enrolled = await api.post(f"/api/v1/course-offerings/{offering}/enroll", headers=database.headers(student))
    assert enrolled.status_code == 201, enrolled.text
    enrollment_id = enrolled.json()["id"]
    dropped = await api.post(
        f"/api/v1/course-offerings/enrollments/{enrollment_id}/drop", headers=database.headers(student),
    )
    assert dropped.status_code == 200, dropped.text
    before = await database.conn.fetchrow("SELECT * FROM course_enrollments")
    if current_term is None:
        await database.conn.execute("DELETE FROM profiles_student WHERE user_id=$1", student.id)
    else:
        await database.conn.execute(
            "UPDATE profiles_student SET current_term=$1 WHERE user_id=$2", current_term, student.id,
        )
    endpoint = (f"/api/v1/course-offerings/enrollments/{enrollment_id}/reselect" if path == "reselect"
                else f"/api/v1/course-offerings/{offering}/enroll")
    result = await api.post(endpoint, headers=database.headers(student), json={"enrollment_type": "improvement"})
    eligible = current_term == "3-1"
    assert result.status_code == ((200 if path == "reselect" else 201) if eligible else 403), result.text
    after = await database.conn.fetchrow("SELECT * FROM course_enrollments")
    if eligible:
        assert after["id"] == enrollment_id
        assert after["status"] == "improvement"
        assert after["enrolled_at"] == before["enrolled_at"]
        assert after["dropped_at"] is None
    else:
        assert after == before
    assert await database.conn.fetchval("SELECT count(*) FROM notification_log") == (2 if eligible else 1)
    assert await database.conn.fetchval("SELECT count(*) FROM notifications") == (2 if eligible else 1)
