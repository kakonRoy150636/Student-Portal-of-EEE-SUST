"""Academic model behavior against Alembic-created PostgreSQL constraints."""
import asyncio
from decimal import Decimal

import asyncpg
import pytest
from sqlalchemy import func, select

from app.models.academic import (
    Course, CourseEnrollment, CourseOffering, TeacherAssignmentRequest,
)

pytestmark = pytest.mark.asyncio


async def active_credits(db, student_id):
    return await db.scalar(
        select(func.coalesce(func.sum(CourseEnrollment.credit_hours), 0)).where(
            CourseEnrollment.student_id == student_id, CourseEnrollment.is_active,
        )
    )


async def test_offering_owner_publication_and_semester_uniqueness(database):
    admin = await database.user("super_admin")
    original = await database.offering(credits=1.5)
    async with database.sessions() as db, db.begin():
        offering = await db.get(CourseOffering, original)
        assert offering.publication_status == "draft"
        assert offering.created_by is None
        offering.created_by = admin.id
        offering.publication_status = "published"
        offering.published_by = admin.id
        offering.published_at = offering.updated_at
        course_id, semester_id = offering.course_id, offering.semester_id

    async with database.sessions() as db:
        offering = await db.get(CourseOffering, original)
        assert offering.created_by == offering.published_by == admin.id
        assert offering.publication_status == "published"
        assert offering.published_at is not None
        assert offering.credit_hours == Decimal("1.5")
    with pytest.raises(asyncpg.UniqueViolationError):
        await database.conn.execute(
            "INSERT INTO course_offerings(course_id,semester_id,created_by) VALUES ($1,$2,$3)",
            course_id, semester_id, admin.id,
        )
    other_semester = await database.semester()
    async with database.sessions() as db, db.begin():
        db.add(CourseOffering(course_id=course_id, semester_id=other_semester, created_by=admin.id))
    with pytest.raises(asyncpg.CheckViolationError):
        await database.conn.execute("UPDATE course_offerings SET publication_status='invalid' WHERE id=$1", original)
    assert await database.conn.fetchval("SELECT publication_status FROM course_offerings WHERE id=$1", original) == "published"


@pytest.mark.parametrize("status", ["pending", "approved", "rejected"])
async def test_teacher_requests_remain_unique_after_decisions(database, status):
    teacher, other_teacher = await database.user("teacher"), await database.user("teacher")
    offering = await database.offering()
    async with database.sessions() as db, db.begin():
        request = TeacherAssignmentRequest(course_offering_id=offering, teacher_id=teacher.id)
        db.add(request)
        await db.flush()
        assert request.status == "pending"
        request.status = status
        request_id = request.id
    async with database.sessions() as db:
        request = await db.get(TeacherAssignmentRequest, request_id)
        assert request.status == status
    with pytest.raises(asyncpg.UniqueViolationError):
        await database.conn.execute(
            "INSERT INTO teacher_assignment_requests(course_offering_id,teacher_id) VALUES ($1,$2)",
            offering, teacher.id,
        )
    await database.conn.execute(
        "INSERT INTO teacher_assignment_requests(course_offering_id,teacher_id) VALUES ($1,$2)",
        offering, other_teacher.id,
    )
    # A request/decision does not create an assignment implicitly.
    assert await database.conn.fetchval("SELECT count(*) FROM course_offering_teachers") == 0
    assert await database.conn.fetchval("SELECT count(*) FROM teacher_assignment_requests") == 2


@pytest.mark.parametrize("table", ["teacher_assignment_requests", "course_enrollments"])
@pytest.mark.parametrize("status", ["invalid", None])
async def test_database_rejects_invalid_or_null_status(database, table, status):
    user = await database.user("teacher" if table == "teacher_assignment_requests" else "student")
    offering = await database.offering()
    actor_column = "teacher_id" if table == "teacher_assignment_requests" else "student_id"
    expected = asyncpg.NotNullViolationError if status is None else asyncpg.CheckViolationError
    with pytest.raises(expected):
        await database.conn.execute(
            f"INSERT INTO {table}(course_offering_id,{actor_column},status) VALUES ($1,$2,$3)",
            offering, user.id, status,
        )


@pytest.mark.parametrize("status", ["enrolled", "main", "improvement", "drop"])
async def test_all_supported_enrollment_statuses_persist(database, status):
    student = await database.user()
    offering = await database.offering(credits=1.5)
    async with database.sessions() as db, db.begin():
        enrollment = CourseEnrollment(student_id=student.id, course_offering_id=offering, status=status)
        db.add(enrollment)
        await db.flush()
        enrollment_id = enrollment.id
    async with database.sessions() as db:
        enrollment = await db.get(CourseEnrollment, enrollment_id)
        assert enrollment.status == status
        assert enrollment.is_active == (status != "drop")
        assert enrollment.credit_hours == Decimal("1.5")
        assert await active_credits(db, student.id) == (0 if status == "drop" else Decimal("1.5"))


@pytest.mark.parametrize("status", ["enrolled", "main", "improvement"])
async def test_drop_then_reselect_preserves_enrollment_identity_and_credits(database, status):
    student = await database.user()
    offering = await database.offering(credits=3)
    await database.enroll(student, offering)
    original = await database.conn.fetchrow("SELECT id,enrolled_at FROM course_enrollments")
    for _ in range(2):
        async with database.sessions() as db, db.begin():
            enrollment = await db.get(CourseEnrollment, original["id"])
            enrollment.drop()
            dropped_at = enrollment.dropped_at
            enrollment.drop()
            assert enrollment.dropped_at == dropped_at
        # The full unique constraint also covers dropped rows.
        with pytest.raises(asyncpg.UniqueViolationError):
            await database.conn.execute(
                "INSERT INTO course_enrollments(student_id,course_offering_id) VALUES ($1,$2)", student.id, offering,
            )
        async with database.sessions() as db, db.begin():
            enrollment = await db.get(CourseEnrollment, original["id"])
            assert await active_credits(db, student.id) == 0
            assert enrollment.dropped_at is not None
            for invalid in ("drop", "invalid"):
                with pytest.raises(ValueError):
                    enrollment.reselect(invalid)
                assert enrollment.status == "drop"
            enrollment.reselect(status)
        async with database.sessions() as db:
            enrollment = await db.get(CourseEnrollment, original["id"])
            assert enrollment.status == status
            assert enrollment.dropped_at is None
            assert enrollment.enrolled_at == original["enrolled_at"]
            assert enrollment.updated_at >= enrollment.enrolled_at
            assert await active_credits(db, student.id) == Decimal("3.0")
    assert await database.conn.fetchval("SELECT count(*) FROM course_enrollments") == 1
    assert await database.conn.fetchval("SELECT id FROM course_enrollments") == original["id"]


async def test_credits_are_read_only_and_follow_catalogue_changes(database):
    student = await database.user()
    offering_id = await database.offering(credits=1.5)
    await database.enroll(student, offering_id)
    async with database.sessions() as db, db.begin():
        offering = await db.get(CourseOffering, offering_id)
        course_id = offering.course_id
        for model, kwargs in (
            (CourseOffering, {"course_id": course_id, "semester_id": offering.semester_id}),
            (CourseEnrollment, {"course_offering_id": offering_id, "student_id": student.id}),
        ):
            with pytest.raises(AttributeError):
                model(**kwargs, credit_hours=Decimal("99"))
        with pytest.raises(AttributeError):
            offering.credit_hours = Decimal("99")
        offering.course.credit_hours = Decimal("4.5")
    async with database.sessions() as db:
        enrollment = await db.scalar(select(CourseEnrollment))
        with pytest.raises(AttributeError):
            enrollment.credit_hours = Decimal("99")
        assert enrollment.credit_hours == enrollment.offering.credit_hours == Decimal("4.5")
        assert await active_credits(db, student.id) == Decimal("4.5")
        assert await db.scalar(select(Course.credit_hours).where(Course.id == course_id)) == Decimal("4.5")


@pytest.mark.parametrize("table,actor_column,role", [
    ("teacher_assignment_requests", "teacher_id", "teacher"),
    ("course_enrollments", "student_id", "student"),
])
async def test_concurrent_inserts_cannot_create_duplicates(database, table, actor_column, role):
    user = await database.user(role)
    offering = await database.offering()

    async def insert():
        conn = await asyncpg.connect(database.dsn)
        try:
            try:
                await conn.execute(
                    f"INSERT INTO {table}(course_offering_id,{actor_column}) VALUES ($1,$2)", offering, user.id,
                )
                return "created"
            except asyncpg.UniqueViolationError:
                return "duplicate"
        finally:
            await conn.close()

    assert sorted(await asyncio.gather(insert(), insert())) == ["created", "duplicate"]
    assert await database.conn.fetchval(f"SELECT count(*) FROM {table}") == 1
