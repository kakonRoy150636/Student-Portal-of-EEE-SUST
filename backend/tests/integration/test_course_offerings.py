"""PostgreSQL concurrency checks for offering and enrollment services."""

import asyncio

import pytest

from app.core.exceptions import ResourceConflictException
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

    results = await asyncio.gather(enroll_once(), enroll_once())
    assert sorted(result[0] for result in results) == ["created", "duplicate"]
    assert await database.conn.fetchval(
        "SELECT count(*) FROM course_enrollments WHERE student_id=$1 AND course_offering_id=$2",
        student.id,
        offering,
    ) == 1
