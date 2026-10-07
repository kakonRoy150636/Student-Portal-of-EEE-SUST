"""Regression coverage for the student's current-semester routine."""

from datetime import date, time
import uuid

import pytest

from app.models.academic import (
    ClassSchedule,
    Course,
    CourseEnrollment,
    CourseOffering,
    Semester,
)
from app.models.facility import Room
from app.services.schedule_service import ScheduleService


async def _scheduled_offering(db, student, *, semester_active: bool, status: str, day: str):
    suffix = uuid.uuid4().hex[:8]
    semester = Semester(
        title=f"Routine Sem {suffix}",
        is_active=semester_active,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 6, 30),
    )
    course = Course(
        course_code=f"R{suffix}",
        title="Routine Test Course",
        credit_hours=3.0,
        type="theory",
        description="fixture",
    )
    db.add_all([semester, course])
    await db.flush()

    offering = CourseOffering(course_id=course.id, semester_id=semester.id)
    room = Room(room_number=f"Routine Room {suffix}", capacity=30, is_lab=False)
    db.add_all([offering, room])
    await db.flush()

    db.add_all([
        CourseEnrollment(course_offering_id=offering.id, student_id=student.id, status=status),
        ClassSchedule(
            course_offering_id=offering.id,
            room_id=room.id,
            instructor_id=student.id,
            day_of_week=day,
            start_time=time(9, 0),
            end_time=time(10, 0),
        ),
    ])
    await db.flush()
    return course


@pytest.mark.asyncio
async def test_my_routine_only_returns_current_active_enrollment_schedules(db, student):
    current_course = await _scheduled_offering(
        db, student, semester_active=True, status="enrolled", day="Monday"
    )
    await _scheduled_offering(db, student, semester_active=True, status="drop", day="Tuesday")
    await _scheduled_offering(db, student, semester_active=False, status="main", day="Wednesday")
    await db.commit()

    routine = await ScheduleService(db).get_my_routine(student.id)

    assert [entry["course_code"] for entry in routine] == [current_course.course_code]
