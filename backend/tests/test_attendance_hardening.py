from datetime import date
import uuid

import pytest
from sqlalchemy import func, select

from app.models.academic import Course, CourseEnrollment, CourseOffering, CourseOfferingTeacher, Semester
from app.models.attendance import AttendanceRecord, AttendanceSession
from app.models.user import UserRole
from app.services.attendance_service import AttendanceService
from tests.conftest import auth_header, make_user


pytestmark = pytest.mark.asyncio


async def _attendance_fixture(db):
    teacher = await make_user(db, role=UserRole.TEACHER)
    student = await make_user(db, role=UserRole.STUDENT)
    stranger = await make_user(db, role=UserRole.STUDENT)
    semester = Semester(
        title=f"Attendance {uuid.uuid4().hex[:8]}",
        is_active=True,
        start_date=date(2030, 1, 1),
        end_date=date(2030, 6, 30),
    )
    course = Course(
        course_code=f"ATT-{uuid.uuid4().hex[:6].upper()}",
        title="Attendance fixture",
        credit_hours=3,
        type="theory",
    )
    db.add_all([semester, course])
    await db.flush()
    offering = CourseOffering(course_id=course.id, semester_id=semester.id)
    db.add(offering)
    await db.flush()
    db.add_all([
        CourseOfferingTeacher(course_offering_id=offering.id, teacher_id=teacher.id),
        CourseEnrollment(course_offering_id=offering.id, student_id=student.id, status="enrolled"),
    ])
    await db.commit()
    return teacher, student, stranger, offering, semester


async def test_attendance_rejects_non_enrolled_students(client, db):
    teacher, _, stranger, offering, _ = await _attendance_fixture(db)
    response = await client.post(
        "/api/v1/attendance/sessions",
        json={
            "course_offering_id": str(offering.id),
            "session_date": "2030-01-08",
            "records": [{"student_id": str(stranger.id), "status": "present"}],
        },
        headers=auth_header(teacher),
    )
    assert response.status_code == 422, response.text
    assert await db.scalar(select(func.count()).select_from(AttendanceSession)) == 0


async def test_attendance_rejects_invalid_or_duplicate_records(client, db):
    teacher, student, _, offering, _ = await _attendance_fixture(db)
    invalid = await client.post(
        "/api/v1/attendance/sessions",
        json={
            "course_offering_id": str(offering.id),
            "session_date": "2030-01-08",
            "records": [{"student_id": str(student.id), "status": "unknown"}],
        },
        headers=auth_header(teacher),
    )
    assert invalid.status_code == 422

    duplicate = await client.post(
        "/api/v1/attendance/sessions",
        json={
            "course_offering_id": str(offering.id),
            "session_date": "2030-01-08",
            "records": [
                {"student_id": str(student.id), "status": "present"},
                {"student_id": str(student.id), "status": "absent"},
            ],
        },
        headers=auth_header(teacher),
    )
    assert duplicate.status_code == 422


async def test_student_attendance_summary_excludes_dropped_enrollment(db):
    teacher, student, _, offering, _ = await _attendance_fixture(db)
    session = AttendanceSession(course_offering_id=offering.id, taken_by=teacher.id)
    db.add(session)
    await db.flush()
    db.add(AttendanceRecord(session_id=session.id, student_id=student.id, status="present"))
    enrollment = await db.scalar(
        select(CourseEnrollment).where(
            CourseEnrollment.course_offering_id == offering.id,
            CourseEnrollment.student_id == student.id,
        )
    )
    enrollment.status = "drop"
    await db.commit()

    summary = await AttendanceService(db).get_student_summary(student.id)
    assert summary["total_classes"] == 0
    assert summary["attended"] == 0
