"""Course workflow notification recipients and transaction boundaries."""

from __future__ import annotations

import uuid
from unittest.mock import Mock

import pytest

from app.models.notification import NotificationPreference
from app.services.course_offering_service import (
    COURSE_ASSIGNMENT_NOTIFICATION,
    COURSE_ENROLLMENT_NOTIFICATION,
    CourseOfferingService,
    assignment_approval_event_id,
)
from app.services.notification_service import NotificationService

pytestmark = pytest.mark.asyncio


async def pending_request(database, offering, teacher):
    return await database.conn.fetchval(
        """INSERT INTO teacher_assignment_requests(course_offering_id,teacher_id)
           VALUES ($1,$2) RETURNING id""",
        offering,
        teacher.id,
    )


async def assigned_teacher(database, offering, teacher):
    await database.conn.execute(
        """INSERT INTO course_offering_teachers(course_offering_id,teacher_id)
           VALUES ($1,$2)""",
        offering,
        teacher.id,
    )


async def test_assignment_approval_notifies_active_students_and_crs_only(api, database):
    admin = await database.user("super_admin")
    teacher = await database.user("teacher")
    student = await database.user("student")
    cr = await database.user("cr")
    inactive_student = await database.user("student", active=False)
    offering = await database.offering(published=True)
    request_id = await pending_request(database, offering, teacher)

    async with database.sessions() as db:
        await CourseOfferingService(db).decide_assignment(request_id, admin.id, "approve")

    rows = await database.conn.fetch(
        "SELECT user_id,event_id,type FROM notification_log WHERE type=$1",
        COURSE_ASSIGNMENT_NOTIFICATION,
    )
    assert {row["user_id"] for row in rows} == {student.id, cr.id}
    assert len({row["event_id"] for row in rows}) == 1
    assert rows[0]["event_id"] == assignment_approval_event_id(request_id)
    assert await database.conn.fetchval(
        "SELECT count(*) FROM notifications WHERE recipient_id=$1", inactive_student.id
    ) == 0

    for user in (student, cr):
        inbox = await api.get("/api/v1/notifications", headers=database.headers(user))
        assert inbox.status_code == 200
        assert len(inbox.json()) == 1
        assert inbox.json()[0]["data_payload"] == {
            "type": COURSE_ASSIGNMENT_NOTIFICATION,
            "url": "/notifications",
        }


async def test_same_approval_event_is_idempotent(database):
    student = await database.user("student")
    event_id = uuid.uuid4()
    async with database.sessions() as db, db.begin():
        first = await NotificationService(db).enqueue(
            student.id, event_id, COURSE_ASSIGNMENT_NOTIFICATION, "high"
        )
        duplicate = await NotificationService(db).enqueue(
            student.id, event_id, COURSE_ASSIGNMENT_NOTIFICATION, "high"
        )
    assert first is not None
    assert duplicate is None
    assert await database.conn.fetchval(
        "SELECT count(*) FROM notification_log WHERE user_id=$1 AND event_id=$2 AND type=$3",
        student.id,
        event_id,
        COURSE_ASSIGNMENT_NOTIFICATION,
    ) == 1
    assert await database.conn.fetchval(
        "SELECT count(*) FROM notifications WHERE recipient_id=$1", student.id
    ) == 1


async def test_enrollment_notifies_student_and_active_assigned_teachers(api, database):
    student = await database.user("student")
    teacher = await database.user("teacher")
    inactive_teacher = await database.user("teacher", active=False)
    offering = await database.offering(published=True)
    await assigned_teacher(database, offering, teacher)
    await assigned_teacher(database, offering, inactive_teacher)

    async with database.sessions() as db:
        enrollment = await CourseOfferingService(db).enroll(student.id, offering)
        enrollment_id = enrollment.id

    rows = await database.conn.fetch(
        "SELECT user_id,event_id FROM notification_log WHERE type=$1",
        COURSE_ENROLLMENT_NOTIFICATION,
    )
    assert {row["user_id"] for row in rows} == {student.id, teacher.id}
    assert len({row["event_id"] for row in rows}) == 1
    assert await database.conn.fetchval(
        "SELECT count(*) FROM notification_log WHERE user_id=$1", inactive_teacher.id
    ) == 0

    student_inbox = await api.get("/api/v1/notifications", headers=database.headers(student))
    teacher_inbox = await api.get("/api/v1/notifications", headers=database.headers(teacher))
    assert len(student_inbox.json()) == len(teacher_inbox.json()) == 1
    assert student_inbox.json()[0]["data_payload"]["type"] == COURSE_ENROLLMENT_NOTIFICATION

    async with database.sessions() as db:
        await CourseOfferingService(db).drop(enrollment_id, student.id)
    assert await database.conn.fetchval(
        "SELECT count(*) FROM notification_log WHERE type=$1", COURSE_ENROLLMENT_NOTIFICATION
    ) == 2

    async with database.sessions() as db:
        await CourseOfferingService(db).reselect(enrollment_id, student.id, "improvement")
    assert await database.conn.fetchval(
        "SELECT count(*) FROM notification_log WHERE type=$1", COURSE_ENROLLMENT_NOTIFICATION
    ) == 4
    assert await database.conn.fetchval(
        "SELECT count(DISTINCT event_id) FROM notification_log WHERE type=$1",
        COURSE_ENROLLMENT_NOTIFICATION,
    ) == 2


async def test_enrollment_preferences_suppress_inbox_and_push_for_one_recipient(database):
    student = await database.user("student")
    teacher = await database.user("teacher")
    offering = await database.offering(published=True)
    await assigned_teacher(database, offering, teacher)

    async with database.sessions() as db:
        db.add(NotificationPreference(
            user_id=student.id,
            per_type={COURSE_ENROLLMENT_NOTIFICATION: {"push": False, "in_app": False}},
        ))
        await db.commit()

    async with database.sessions() as db:
        await CourseOfferingService(db).enroll(student.id, offering)

    suppressed = await database.conn.fetchrow(
        "SELECT status FROM notification_log WHERE user_id=$1 AND type=$2",
        student.id,
        COURSE_ENROLLMENT_NOTIFICATION,
    )
    assert suppressed["status"] == "complete"
    assert await database.conn.fetchval(
        "SELECT count(*) FROM notifications WHERE recipient_id=$1", student.id
    ) == 0
    assert await database.conn.fetchval(
        "SELECT count(*) FROM notification_batches WHERE user_id=$1", student.id
    ) == 0
    assert await database.conn.fetchval(
        "SELECT count(*) FROM notifications WHERE recipient_id=$1", teacher.id
    ) == 1


async def test_committed_push_batch_reuses_existing_delivery_task(database, monkeypatch):
    from app.tasks import notifications as tasks

    student = await database.user("student")
    offering = await database.offering(published=True)
    async with database.sessions() as db:
        await NotificationService(db).register_device(student.id, "course-enrollment-device")

    published = Mock()
    monkeypatch.setattr(tasks.deliver_notification, "delay", published)
    async with database.sessions() as db:
        await CourseOfferingService(db).enroll(student.id, offering)

    published.assert_called_once()
    batch_id = published.call_args.args[0]
    assert await database.conn.fetchval(
        "SELECT status FROM notification_batches WHERE id=$1", uuid.UUID(batch_id)
    ) == "pending"


async def test_approval_notification_failure_rolls_back_assignment_and_outbox(database, monkeypatch):
    admin = await database.user("super_admin")
    teacher = await database.user("teacher")
    await database.user("student")
    offering = await database.offering(published=True)
    request_id = await pending_request(database, offering, teacher)

    enqueue = NotificationService.enqueue

    async def fail_enqueue(self, *args, **kwargs):
        await enqueue(self, *args, **kwargs)
        raise RuntimeError("forced notification failure")

    monkeypatch.setattr(NotificationService, "enqueue", fail_enqueue)
    with pytest.raises(RuntimeError):
        async with database.sessions() as db:
            await CourseOfferingService(db).decide_assignment(request_id, admin.id, "approve")

    assert await database.conn.fetchval(
        "SELECT status FROM teacher_assignment_requests WHERE id=$1", request_id
    ) == "pending"
    assert await database.conn.fetchval(
        "SELECT count(*) FROM course_offering_teachers WHERE course_offering_id=$1", offering
    ) == 0
    assert await database.conn.fetchval("SELECT count(*) FROM notification_log") == 0
    assert await database.conn.fetchval("SELECT count(*) FROM notifications") == 0
    assert await database.conn.fetchval("SELECT count(*) FROM notification_batches") == 0


async def test_enrollment_notification_failure_rolls_back_enrollment_and_outbox(database, monkeypatch):
    student = await database.user("student")
    offering = await database.offering(published=True)

    async def fail_enqueue(self, *args, **kwargs):
        raise RuntimeError("forced notification failure")

    monkeypatch.setattr(NotificationService, "enqueue", fail_enqueue)
    with pytest.raises(RuntimeError):
        async with database.sessions() as db:
            await CourseOfferingService(db).enroll(student.id, offering)

    assert await database.conn.fetchval(
        "SELECT count(*) FROM course_enrollments WHERE student_id=$1", student.id
    ) == 0
    assert await database.conn.fetchval("SELECT count(*) FROM notification_log") == 0
    assert await database.conn.fetchval("SELECT count(*) FROM notifications") == 0


async def test_partial_notification_failure_does_not_publish_aborted_batches_on_retry(database, monkeypatch):
    from app.tasks import notifications as tasks

    student = await database.user()
    teacher = await database.user("teacher")
    offering = await database.offering(published=True, teacher=teacher)
    async with database.sessions() as db:
        await NotificationService(db).register_device(student.id, "rollback-enrollment-device")

    enqueue = NotificationService.enqueue
    published = Mock()
    monkeypatch.setattr(tasks.deliver_notification, "delay", published)

    async def fail_for_teacher(self, user_id, *args, **kwargs):
        result = await enqueue(self, user_id, *args, **kwargs)
        if user_id == teacher.id:
            raise RuntimeError("failure after student and teacher outbox writes")
        return result

    monkeypatch.setattr(NotificationService, "enqueue", fail_for_teacher)
    async with database.sessions() as db:
        service = CourseOfferingService(db)
        with pytest.raises(RuntimeError):
            await service.enroll(student.id, offering)
        published.assert_not_called()
        for table in ("course_enrollments", "notification_log", "notifications", "notification_batches"):
            assert await database.conn.fetchval(f"SELECT count(*) FROM {table}") == 0

        monkeypatch.setattr(NotificationService, "enqueue", enqueue)
        await service.enroll(student.id, offering)

    published.assert_called_once()
    assert await database.conn.fetchval(
        "SELECT status FROM notification_batches WHERE id=$1", uuid.UUID(published.call_args.args[0]),
    ) == "pending"


async def test_reselection_notification_failure_preserves_dropped_row_and_outbox(database, monkeypatch):
    student = await database.user()
    offering = await database.offering(published=True)
    async with database.sessions() as db:
        service = CourseOfferingService(db)
        enrollment = await service.enroll(student.id, offering)
        await service.drop(enrollment.id, student.id)
    original = await database.conn.fetchrow("SELECT * FROM course_enrollments")
    counts = {table: await database.conn.fetchval(f"SELECT count(*) FROM {table}") for table in (
        "notification_log", "notifications", "notification_batches",
    )}
    enqueue = NotificationService.enqueue

    async def fail_after_enqueue(self, *args, **kwargs):
        await enqueue(self, *args, **kwargs)
        raise RuntimeError("failure after reselection notification write")

    monkeypatch.setattr(NotificationService, "enqueue", fail_after_enqueue)
    async with database.sessions() as db:
        with pytest.raises(RuntimeError):
            await CourseOfferingService(db).reselect(original["id"], student.id, "improvement")

    assert await database.conn.fetchrow("SELECT * FROM course_enrollments") == original
    for table, count in counts.items():
        assert await database.conn.fetchval(f"SELECT count(*) FROM {table}") == count


async def test_registration_notification_failure_rolls_back_account_profile_and_all_selections(database, monkeypatch):
    from app.schemas.auth import StudentRegisterRequest
    from app.services.auth_service import AuthService

    semester = await database.semester()
    offerings = [await database.offering(semester=semester, published=True) for _ in range(2)]
    request = StudentRegisterRequest.model_validate(database.registration(offerings))
    enqueue = NotificationService.enqueue

    async def fail_after_enqueue(self, *args, **kwargs):
        await enqueue(self, *args, **kwargs)
        raise RuntimeError("failure after registration notification write")

    monkeypatch.setattr(NotificationService, "enqueue", fail_after_enqueue)
    async with database.sessions() as db:
        with pytest.raises(RuntimeError):
            await AuthService(db).register_student(request)

    for table in ("users", "profiles_student", "course_enrollments", "notification_log", "notifications", "notification_batches"):
        assert await database.conn.fetchval(f"SELECT count(*) FROM {table}") == 0


async def test_broker_failure_keeps_complete_enrollment_and_recoverable_outbox(api, database, monkeypatch):
    from app.tasks import notifications as tasks

    student = await database.user()
    offering = await database.offering(published=True)
    async with database.sessions() as db:
        await NotificationService(db).register_device(student.id, "broker-failure-device")
    published = Mock(side_effect=ConnectionError("disposable broker unavailable"))
    monkeypatch.setattr(tasks.deliver_notification, "delay", published)

    result = await api.post(f"/api/v1/course-offerings/{offering}/enroll", headers=database.headers(student))
    assert result.status_code == 201, result.text
    assert result.json()["status"] == "enrolled"
    published.assert_called_once()
    batch_id = uuid.UUID(published.call_args.args[0])
    assert await database.conn.fetchval("SELECT count(*) FROM course_enrollments") == 1
    assert await database.conn.fetchval("SELECT count(*) FROM notifications WHERE recipient_id=$1", student.id) == 1
    assert await database.conn.fetchval("SELECT status FROM notification_batches WHERE id=$1", batch_id) == "pending"
    assert await database.conn.fetchval("SELECT status FROM notification_log WHERE batch_id=$1", batch_id) == "assigned"
    assert await database.conn.fetchval("SELECT status FROM notification_deliveries WHERE batch_id=$1", batch_id) == "pending"
