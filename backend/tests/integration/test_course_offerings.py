"""PostgreSQL concurrency checks for offering and enrollment services."""

import asyncio

import pytest
from sqlalchemy import text

from app.core.exceptions import ResourceConflictException
from app.models.academic import CourseEnrollment
from app.services.course_offering_service import CourseOfferingService

pytestmark = pytest.mark.asyncio


async def test_concurrent_service_enrollment_creates_one_active_row(database):
    student = await database.user()
    offering = await database.offering(published=True)

    async def enroll_once():
        async with database.sessions() as db:
            try:
                enrollment = await CourseOfferingService(db).enroll(student.id, offering)
                return "created", enrollment.id
            except ResourceConflictException:
                return "duplicate", None

    results = await asyncio.wait_for(asyncio.gather(enroll_once(), enroll_once()), timeout=10)
    assert sorted(result[0] for result in results) == ["created", "duplicate"]
    assert await database.conn.fetchval(
        "SELECT count(*) FROM course_enrollments WHERE student_id=$1 AND course_offering_id=$2",
        student.id,
        offering,
    ) == 1


async def test_select_and_reselect_race_on_dropped_row_has_no_deadlock(database, monkeypatch):
    student = await database.user()
    offering = await database.offering(published=True)
    await database.enroll(student, offering)
    original_id = await database.conn.fetchval("SELECT id FROM course_enrollments")
    await database.conn.execute("UPDATE course_enrollments SET status='drop' WHERE id=$1", original_id)

    offering_locked = asyncio.Event()
    resume_selection = asyncio.Event()
    original_lookup = CourseOfferingService._enrollment_offerings

    async def lock_then_wait(self, *args, **kwargs):
        result = await original_lookup(self, *args, **kwargs)
        if asyncio.current_task().get_name() == "select-dropped":
            offering_locked.set()
            await resume_selection.wait()
        return result

    monkeypatch.setattr(CourseOfferingService, "_enrollment_offerings", lock_then_wait)

    async def change(action):
        async with database.sessions() as db:
            if action == "reselect":
                await db.execute(text("SELECT set_config('application_name', 'course-reselect-race', true)"))
            try:
                service = CourseOfferingService(db)
                enrollment = (await service.enroll(student.id, offering) if action == "select"
                              else await service.reselect(original_id, student.id))
                return enrollment.id
            except ResourceConflictException:
                return None

    async def wait_for_reselection_lock():
        while not await database.conn.fetchval("""SELECT EXISTS (
            SELECT 1 FROM pg_stat_activity WHERE datname=current_database()
            AND application_name='course-reselect-race' AND wait_event_type='Lock')"""):
            await asyncio.sleep(0.01)

    selection = asyncio.create_task(change("select"), name="select-dropped")
    reselection = None
    try:
        await asyncio.wait_for(offering_locked.wait(), timeout=10)
        reselection = asyncio.create_task(change("reselect"), name="reselect-dropped")
        # Wait for a real database lock, not a timing assumption. On the old
        # order, reselection holds the enrollment while waiting for the offering.
        await asyncio.wait_for(wait_for_reselection_lock(), timeout=10)
        resume_selection.set()
        results = await asyncio.wait_for(asyncio.gather(selection, reselection), timeout=10)
        assert results == [original_id, None]
    finally:
        resume_selection.set()
        tasks = [task for task in (selection, reselection) if task is not None]
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    assert await database.conn.fetchval("SELECT count(*) FROM course_enrollments") == 1


@pytest.mark.parametrize("action", ["enroll", "reselect"])
async def test_concurrent_http_enrollment_returns_one_success_and_one_conflict(api, database, action):
    student = await database.user()
    offering = await database.offering(published=True)
    if action == "reselect":
        await database.enroll(student, offering)
        original_id = await database.conn.fetchval("SELECT id FROM course_enrollments")
        await database.conn.execute("UPDATE course_enrollments SET status='drop' WHERE id=$1", original_id)
        path = f"/api/v1/course-offerings/enrollments/{original_id}/reselect"
    else:
        original_id = None
        path = f"/api/v1/course-offerings/{offering}/enroll"

    async def request():
        return await api.post(path, headers=database.headers(student))

    responses = await asyncio.wait_for(asyncio.gather(request(), request()), timeout=10)
    assert sorted(response.status_code for response in responses) == [200 if action == "reselect" else 201, 409]
    assert await database.conn.fetchval("SELECT count(*) FROM course_enrollments") == 1
    row = await database.conn.fetchrow("SELECT id,status FROM course_enrollments")
    assert row["status"] == "enrolled"
    if original_id is not None:
        assert row["id"] == original_id
    assert await database.conn.fetchval("SELECT count(*) FROM notification_log WHERE type='course_enrollment'") == 1


async def test_active_credits_exclude_dropped_historical_and_other_students(api, database):
    student, other = await database.user(), await database.user()
    active_semester, historical_semester = await database.semester(), await database.semester()
    await database.conn.execute("UPDATE semesters SET is_active=false WHERE id=$1", historical_semester)
    for status, credits in (("enrolled", 3), ("main", 1.5), ("improvement", 3), ("drop", 4.5)):
        offering = await database.offering(credits, semester=active_semester, published=True)
        await database.conn.execute(
            "INSERT INTO course_enrollments(student_id,course_offering_id,status) VALUES ($1,$2,$3)",
            student.id, offering, status,
        )
    historical = await database.offering(3, semester=historical_semester, published=True)
    await database.enroll(student, historical)
    await database.enroll(other, await database.offering(4.5, semester=active_semester, published=True))

    response = await api.get("/api/v1/course-offerings/enrollments/me/credits", headers=database.headers(student))
    assert response.status_code == 200
    assert response.json() == {"active_credit_total": 7.5}
    history = await api.get("/api/v1/course-offerings/enrollments/me", headers=database.headers(student))
    assert len(history.json()) == 5  # historical and dropped rows remain in history, not in the total


async def test_reselection_checks_current_status_even_with_cached_dropped_enrollment(database):
    student = await database.user()
    offering = await database.offering(published=True)
    await database.enroll(student, offering)
    enrollment_id = await database.conn.fetchval("SELECT id FROM course_enrollments")
    await database.conn.execute("UPDATE course_enrollments SET status='drop' WHERE id=$1", enrollment_id)

    async with database.sessions() as cached_db:
        cached = await cached_db.get(CourseEnrollment, enrollment_id)
        assert cached.status == "drop"
        async with database.sessions() as other_db:
            await CourseOfferingService(other_db).reselect(enrollment_id, student.id)
        with pytest.raises(ResourceConflictException):
            await CourseOfferingService(cached_db).reselect(enrollment_id, student.id)

    assert await database.conn.fetchval("SELECT status FROM course_enrollments") == "enrolled"
    assert await database.conn.fetchval("SELECT count(*) FROM notification_log WHERE type='course_enrollment'") == 1
