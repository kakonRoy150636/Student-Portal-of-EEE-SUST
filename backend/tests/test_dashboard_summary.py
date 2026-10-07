"""Contract tests for GET /dashboard/summary.

The dashboards used to render frozen strings ("88.5%", "04 COURSES", "12 TO
REVIEW"). These tests pin the two properties that make the new endpoint
trustworthy: the numbers actually come from the rows that exist, and a caller
only ever receives the section for their own role.
"""
from datetime import date
import uuid

import pytest

from app.models.academic import CourseEnrollment, CourseOffering
from app.models.attendance import AttendanceRecord, AttendanceSession
from app.models.user import User, UserRole

from .conftest import auth_header, make_user


async def _offering_for(
    db,
    student: User,
    *,
    semester_active: bool = True,
    status: str = "enrolled",
    credits: float = 3.0,
) -> CourseOffering:
    """A course offering plus an enrolment for ``student``."""
    from app.models.academic import Course, Semester

    # SQLite's Date type rejects ISO strings (Postgres would coerce them).
    suffix = uuid.uuid4().hex[:8]
    semester = Semester(
        title=f"Sem {suffix}",
        is_active=semester_active,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 6, 30),
    )
    db.add(semester)
    await db.flush()

    course = Course(course_code=f"EEE {suffix}", title="Test Course",
                    credit_hours=credits, type="theory", description="fixture")
    db.add(course)
    await db.flush()

    offering = CourseOffering(course_id=course.id, semester_id=semester.id)
    db.add(offering)
    await db.flush()

    db.add(CourseEnrollment(course_offering_id=offering.id, student_id=student.id, status=status))
    await db.commit()
    return offering


@pytest.mark.asyncio
async def test_summary_requires_authentication(client):
    resp = await client.get("/api/v1/dashboard/summary")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_sees_department_counts(client, db, admin):
    await make_user(db, role=UserRole.STUDENT)
    await make_user(db, role=UserRole.TEACHER, is_active=False)

    resp = await client.get("/api/v1/dashboard/summary", headers=auth_header(admin))
    assert resp.status_code == 200
    body = resp.json()

    assert body["role"] == "super_admin"
    assert body["admin"]["users_total"] == 3          # admin + student + pending teacher
    assert body["admin"]["pending_approvals"] == 1    # the inactive teacher
    assert body["admin"]["users_by_role"]["student"] == 1
    assert body["admin"]["users_by_role"]["teacher"] == 1
    # Role isolation: an admin payload carries no student section.
    assert body["student"] is None


@pytest.mark.asyncio
async def test_student_section_reflects_real_attendance_rows(client, db, student):
    offering = await _offering_for(db, student)

    session = AttendanceSession(course_offering_id=offering.id, taken_by=student.id)
    db.add(session)
    await db.flush()
    # Two of three classes attended -> 66.67%, i.e. below the 75% rule.
    for status in ("present", "late", "absent"):
        db.add(AttendanceRecord(session_id=session.id, student_id=student.id, status=status))
    await db.commit()

    resp = await client.get("/api/v1/dashboard/summary", headers=auth_header(student))
    assert resp.status_code == 200
    body = resp.json()

    assert body["role"] == "student"
    s = body["student"]
    assert s["total_classes"] == 3
    assert s["attended"] == 2
    assert s["attendance_percentage"] == pytest.approx(66.67, abs=0.01)
    assert s["below_attendance_threshold"] is True
    assert s["enrolled_courses"] == 1
    assert s["credit_hours"] == pytest.approx(3.0)
    # A student must never receive department-wide totals.
    assert body["admin"] is None
    assert body["teacher"] is None


@pytest.mark.asyncio
async def test_student_summary_counts_only_current_active_enrollments(client, db, student):
    await _offering_for(db, student, credits=3.0)
    await _offering_for(db, student, status="drop", credits=2.0)
    await _offering_for(db, student, semester_active=False, status="main", credits=4.0)

    resp = await client.get("/api/v1/dashboard/summary", headers=auth_header(student))
    assert resp.status_code == 200
    summary = resp.json()["student"]

    assert summary["enrolled_courses"] == 1
    assert summary["credit_hours"] == pytest.approx(3.0)


@pytest.mark.asyncio
async def test_no_attendance_rows_yields_null_not_a_fake_zero_percent(client, db, student):
    """An empty database must read as 'unknown', not as a poor 0% score."""
    resp = await client.get("/api/v1/dashboard/summary", headers=auth_header(student))
    assert resp.status_code == 200
    s = resp.json()["student"]

    assert s["total_classes"] == 0
    assert s["attendance_percentage"] is None
    assert s["below_attendance_threshold"] is None
    assert s["routine"] == []


@pytest.mark.asyncio
async def test_teacher_section_only_counts_assigned_offerings(client, db, teacher):
    other_teacher = await make_user(db, role=UserRole.TEACHER)
    student = await make_user(db, role=UserRole.STUDENT)
    offering = await _offering_for(db, student)

    from app.models.academic import CourseOfferingTeacher

    db.add(CourseOfferingTeacher(course_offering_id=offering.id, teacher_id=other_teacher.id))
    await db.commit()

    resp = await client.get("/api/v1/dashboard/summary", headers=auth_header(teacher))
    assert resp.status_code == 200
    t = resp.json()["teacher"]
    # The offering belongs to a different teacher, so nothing may be attributed here.
    assert t["assigned_courses"] == 0
    assert t["students_taught"] == 0
