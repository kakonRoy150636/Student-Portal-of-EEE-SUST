"""Real migrated PostgreSQL workspace, locking and notification outbox tests."""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import asyncpg
import pytest

from app.services.course_workspace_service import CourseWorkspaceService, announcement_event_id
from app.services.notification_dispatch import deliver_batch
from app.services.notification_service import NotificationService

pytestmark = pytest.mark.asyncio


async def test_concurrent_publish_read_and_notification_delivery(api, database, monkeypatch):
    from app.tasks.notifications import deliver_notification

    teacher, student, excluded = await database.user("teacher"), await database.user(), await database.user()
    offering = await database.offering(teacher=teacher, published=True)
    await database.enroll(student, offering)
    await database.enroll(excluded, offering)
    await database.conn.execute("UPDATE course_enrollments SET status='drop' WHERE student_id=$1", excluded.id)
    async with database.sessions() as db:
        await NotificationService(db).register_device(student.id, "workspace-test-device")
    publisher = Mock()
    monkeypatch.setattr(deliver_notification, "delay", publisher)
    path = f"/api/v1/course-offerings/{offering}/announcements"
    draft = await api.post(path, headers=database.headers(teacher), json={
        "title": "Private course title", "body": "Plain text only", "announcement_type": "urgent",
    })
    assert draft.status_code == 201, draft.text
    ident = uuid.UUID(draft.json()["id"])
    results = await asyncio.wait_for(asyncio.gather(*[
        api.post(f"{path}/{ident}/publish", headers=database.headers(teacher)) for _ in range(2)
    ]), 10)
    assert [result.status_code for result in results] == [200, 200]
    assert results[0].json()["publish_at"] == results[1].json()["publish_at"]
    assert await database.conn.fetchval("SELECT count(*) FROM notification_log") == 1
    log = await database.conn.fetchrow("SELECT * FROM notification_log")
    assert log["user_id"] == student.id
    assert log["event_id"] == announcement_event_id(ident, student.id)
    assert log["priority"] == "high"
    publisher.assert_called_once()
    sender = Mock(return_value="fcm-workspace-message")
    await deliver_batch(database.sessions, log["batch_id"], datetime.now(timezone.utc) + timedelta(minutes=1), sender)
    await deliver_batch(database.sessions, log["batch_id"], datetime.now(timezone.utc) + timedelta(minutes=2), sender)
    sender.assert_called_once()
    assert sender.call_args.kwargs["priority"] == "high"
    assert "Private course title" not in str(sender.call_args)
    reads = await asyncio.wait_for(asyncio.gather(*[
        api.patch(f"/api/v1/course-announcements/{ident}/read", headers=database.headers(student)) for _ in range(2)
    ]), 10)
    assert [result.status_code for result in reads] == [200, 200]
    assert reads[0].json() == reads[1].json()
    assert await database.conn.fetchval("SELECT count(*) FROM announcement_reads") == 1


async def test_scheduled_workers_publish_once_at_due_time_with_current_recipients(api, database):
    teacher, student, cr = await database.user("teacher"), await database.user(), await database.user("cr")
    offering = await database.offering(teacher=teacher, published=True)
    await database.enroll(student, offering)
    due = datetime.now(timezone.utc) + timedelta(hours=1)
    created = await api.post(f"/api/v1/course-offerings/{offering}/announcements", headers=database.headers(teacher), json={
        "title": "Scheduled", "body": "For CRs", "audience": "cr_only", "status": "scheduled", "publish_at": due.isoformat(),
    })
    assert created.status_code == 201, created.text
    # Eligibility is evaluated at publication, including enrollment after the
    # draft was scheduled.
    await database.enroll(cr, offering)
    assert await database.conn.fetchval("SELECT count(*) FROM notification_log") == 0

    async def run(at):
        async with database.sessions() as db:
            return await CourseWorkspaceService(db).publish_due_announcements(at)

    assert await run(due - timedelta(seconds=1)) == 0
    published = await asyncio.wait_for(asyncio.gather(run(due), run(due)), 10)
    assert sum(published) == 1
    assert await run(due + timedelta(minutes=1)) == 0
    assert await database.conn.fetchval("SELECT status FROM course_announcements") == "published"
    rows = await database.conn.fetch("SELECT user_id, priority FROM notification_log")
    assert [tuple(row) for row in rows] == [(cr.id, "medium")]


async def test_migration_constraints_indexes_and_cascade(api, database):
    teacher, student = await database.user("teacher"), await database.user()
    offering = await database.offering(teacher=teacher, published=True)
    await database.enroll(student, offering)
    assert await database.conn.fetchval("SELECT version_num FROM alembic_version") == "20261012_0012"
    indices = {row[0] for row in await database.conn.fetch("SELECT indexname FROM pg_indexes WHERE schemaname='public'")}
    assert {"ix_course_announcements_due", "ix_course_announcements_offering_feed",
            "ix_announcement_reads_announcement_user_read"} <= indices
    constraints = {row[0] for row in await database.conn.fetch(
        """SELECT conname FROM pg_constraint c JOIN pg_class r ON r.oid=c.conrelid
           WHERE r.relname='announcement_reads'"""
    )}
    assert {"pk_announcement_reads", "announcement_reads_announcement_id_fkey",
            "announcement_reads_user_id_fkey"} <= constraints
    insert = """INSERT INTO course_announcements(offering_id,author_id,title,body,audience,status,publish_at)
                VALUES ($1,$2,'Test','Plain text',$3,$4,$5) RETURNING id"""
    with pytest.raises(asyncpg.CheckViolationError):
        await database.conn.fetchval(insert, offering, teacher.id, "selected_users", "draft", None)
    with pytest.raises(asyncpg.CheckViolationError):
        await database.conn.fetchval(insert, offering, teacher.id, "enrolled_students", "scheduled", None)
    announcement = await database.conn.fetchval(insert, offering, teacher.id, "enrolled_students", "published", datetime.now(timezone.utc))
    await database.conn.execute("INSERT INTO announcement_reads(announcement_id,user_id) VALUES ($1,$2)", announcement, student.id)
    with pytest.raises(asyncpg.UniqueViolationError):
        await database.conn.execute("INSERT INTO announcement_reads(announcement_id,user_id) VALUES ($1,$2)", announcement, student.id)
    await database.conn.execute("DELETE FROM course_offerings WHERE id=$1", offering)
    assert await database.conn.fetchval("SELECT count(*) FROM course_announcements") == 0
    assert await database.conn.fetchval("SELECT count(*) FROM announcement_reads") == 0
