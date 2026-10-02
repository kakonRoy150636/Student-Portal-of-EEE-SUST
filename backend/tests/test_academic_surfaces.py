"""Endpoints that used to return hardcoded literals now read real tables.

The regression these guard against is subtle: a stub returns HTTP 200 with
plausible content, so no test of the response *shape* would ever catch it.
Each test here seeds rows and asserts the response reflects them -- which a
constant cannot do.
"""
import uuid
from datetime import date, time, timedelta

import pytest

from app.models.academic import (
    ClassSchedule,
    Course,
    CourseEnrollment,
    CourseOffering,
    CourseOfferingTeacher,
    Semester,
)
from app.models.career import CareerOpportunity
from app.models.facility import Room
from app.models.project import Project, ProjectMember
from app.models.user import UserRole
from tests.conftest import auth_header, make_user

pytestmark = pytest.mark.asyncio


async def _seed_offering(db, *, code="EEE 311", title="Electrical Machines II", day="Sunday"):
    semester = Semester(title=f"3-1 {uuid.uuid4().hex[:4]}", is_active=True,
                        start_date=date.today(), end_date=date.today() + timedelta(days=120))
    db.add(semester)
    await db.flush()
    course = Course(course_code=code, title=title, credit_hours=3.0, type="theory")
    db.add(course)
    await db.flush()
    offering = CourseOffering(course_id=course.id, semester_id=semester.id)
    db.add(offering)
    await db.flush()
    room = Room(room_number=f"R-{uuid.uuid4().hex[:4]}", building="IICT", capacity=40, is_lab=False)
    db.add(room)
    await db.flush()
    schedule = ClassSchedule(
        course_offering_id=offering.id,
        room_id=room.id,
        day_of_week=day,
        start_time=time(9, 0),
        end_time=time(10, 30),
    )
    db.add(schedule)
    await db.commit()
    return course, offering, schedule


async def test_courses_lists_enrolments_not_literals(client, db):
    student = await make_user(db)
    course, offering, _ = await _seed_offering(db)
    db.add(CourseEnrollment(course_offering_id=offering.id, student_id=student.id, status="main"))
    await db.commit()

    response = await client.get("/api/v1/courses", headers=auth_header(student))
    assert response.status_code == 200, response.text
    codes = [row["course_code"] for row in response.json()]
    # The old stub returned "EEE 311" and "EEE 312" for everyone; the real
    # answer contains exactly the one offering this student is enrolled in.
    assert codes == [course.course_code]
    assert response.json()[0]["enrolled_students"] == 1


async def test_courses_are_scoped_to_the_teacher(client, db):
    teacher = await make_user(db, role=UserRole.TEACHER, identifier="faculty-x")
    other_teacher = await make_user(
        db, role=UserRole.TEACHER, identifier="faculty-y", email="y@sust.edu"
    )
    _, mine, _ = await _seed_offering(db, code="EEE 401")
    _, theirs, _ = await _seed_offering(db, code="EEE 402")
    db.add(CourseOfferingTeacher(course_offering_id=mine.id, teacher_id=teacher.id))
    db.add(CourseOfferingTeacher(course_offering_id=theirs.id, teacher_id=other_teacher.id))
    await db.commit()

    response = await client.get("/api/v1/courses", headers=auth_header(teacher))
    assert [row["course_code"] for row in response.json()] == ["EEE 401"]


async def test_routine_comes_from_the_timetable(client, db):
    student = await make_user(db)
    _, offering, schedule = await _seed_offering(db)
    db.add(CourseEnrollment(course_offering_id=offering.id, student_id=student.id, status="main"))
    await db.commit()

    response = await client.get("/api/v1/schedules/my-routine", headers=auth_header(student))
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == str(schedule.id)
    assert body[0]["course_code"] == "EEE 311"
    assert body[0]["start_time"] == "9:00 AM"
    assert body[0]["day_of_week"] == "Sunday"


async def test_routine_excludes_dropped_courses_and_other_students(client, db):
    student = await make_user(db)
    other = await make_user(db, identifier="2023000002", email="other2@sust.edu")
    _, offering, _ = await _seed_offering(db)
    db.add(CourseEnrollment(course_offering_id=offering.id, student_id=other.id, status="main"))
    db.add(CourseEnrollment(course_offering_id=offering.id, student_id=student.id, status="drop"))
    await db.commit()

    response = await client.get("/api/v1/schedules/my-routine", headers=auth_header(student))
    assert response.json() == []


async def test_career_returns_only_verified_unexpired(client, db):
    student = await make_user(db)
    admin = await make_user(db, role=UserRole.SUPER_ADMIN, identifier="admin-1")
    db.add(
        CareerOpportunity(
            posted_by=admin.id, title="Live opening", organization_name="Org A",
            type="internship", application_deadline=date.today() + timedelta(days=5),
            application_target="https://a.test", description="Open now", tags=["vlsi"],
            is_verified=True,
        )
    )
    db.add(
        CareerOpportunity(
            posted_by=admin.id, title="Expired opening", organization_name="Org B",
            type="internship", application_deadline=date.today() - timedelta(days=1),
            application_target="https://b.test", description="Gone", is_verified=True,
        )
    )
    db.add(
        CareerOpportunity(
            posted_by=admin.id, title="Unverified opening", organization_name="Org C",
            type="internship", application_deadline=date.today() + timedelta(days=9),
            application_target="https://c.test", description="Unchecked", is_verified=False,
        )
    )
    await db.commit()

    response = await client.get("/api/v1/career/opportunities", headers=auth_header(student))
    assert response.status_code == 200, response.text
    titles = [row["title"] for row in response.json()]
    assert titles == ["Live opening"]
    assert response.json()[0]["organization_name"] == "Org A"


async def test_projects_include_supervisor_and_team_size(client, db):
    student = await make_user(db)
    teacher = await make_user(db, role=UserRole.TEACHER, identifier="faculty-z")
    semester = Semester(title="4-1", is_active=False,
                        start_date=date.today(), end_date=date.today() + timedelta(days=100))
    db.add(semester)
    await db.flush()
    project = Project(
        title="Grid-scale storage", abstract="A capstone on storage sizing.",
        tier="capstone_thesis", semester_id=semester.id, supervisor_id=teacher.id,
    )
    db.add(project)
    await db.flush()
    db.add(ProjectMember(project_id=project.id, student_id=student.id, role="lead"))
    await db.commit()

    response = await client.get("/api/v1/projects", headers=auth_header(student))
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body) == 1
    assert body[0]["title"] == "Grid-scale storage"
    assert body[0]["supervisor_name"] == teacher.full_name
    assert body[0]["member_count"] == 1


async def test_public_data_endpoints_still_require_authentication(client):
    for path in ("/api/v1/courses", "/api/v1/schedules/my-routine",
                 "/api/v1/career/opportunities", "/api/v1/projects"):
        response = await client.get(path)
        assert response.status_code == 401, path
