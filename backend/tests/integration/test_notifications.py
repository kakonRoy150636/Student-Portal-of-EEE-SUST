import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import asyncpg
import pytest

from app.tasks.notifications import scan_upcoming_class_alerts

pytestmark = pytest.mark.asyncio


async def arrange(database):
    teacher, student = await database.user('teacher'), await database.user()
    offering = await database.offering(teacher=teacher)
    await database.enroll(student, offering)
    schedule = await database.schedule(offering, teacher, await database.room())
    starts = datetime.now(ZoneInfo('Asia/Dhaka')) + timedelta(minutes=5)
    await database.conn.execute('''UPDATE class_schedules SET day_of_week=$1,start_time=$2,end_time=$3
        WHERE id=$4''', starts.strftime('%A').lower(), starts.time().replace(tzinfo=None),
        (starts+timedelta(minutes=45)).time().replace(tzinfo=None), schedule)
    await database.conn.execute('INSERT INTO notification_preferences(user_id) VALUES ($1)', student.id)
    await database.conn.execute("INSERT INTO user_devices(user_id,fcm_token) VALUES ($1,'test-fcm-token')", student.id)
    return student, schedule


async def test_database_deduplicates_concurrent_class_alerts(database):
    student, schedule = await arrange(database)
    barrier = asyncio.Barrier(2)
    async def insert():
        conn = await asyncpg.connect(database.dsn)
        try:
            await barrier.wait()
            return await conn.fetchval('''INSERT INTO notifications(recipient_id,title,body,class_session_id)
                VALUES ($1,'Class alert','Starts shortly',$2)
                ON CONFLICT ON CONSTRAINT uq_notification_class_session DO NOTHING RETURNING id''', student.id, schedule)
        finally:
            await conn.close()
    rows = await asyncio.wait_for(asyncio.gather(insert(), insert()), 10)
    assert sum(row is not None for row in rows) == 1
    assert await database.conn.fetchval('SELECT count(*) FROM notifications') == 1


@pytest.mark.xfail(strict=True, raises=AssertionError, reason='NOT-1: scanner logs only; neither creates nor dispatches alerts')
async def test_scanner_creates_one_alert_then_deduplicates(api, database, monkeypatch):
    from app.core import database as database_module
    from app.integrations import firebase_client
    from unittest.mock import Mock
    student, schedule = await arrange(database)
    monkeypatch.setattr(database_module, 'AsyncSessionLocal', database.sessions)
    # External FCM delivery is the only mocked boundary; scanner itself is real.
    push = Mock(return_value=True)
    monkeypatch.setattr(firebase_client, 'dispatch_push_notification', push)
    await asyncio.to_thread(scan_upcoming_class_alerts.run)
    # This positive assertion prevents the log-only stub from vacuously passing
    # a "no duplicates" test that would otherwise accept zero notifications.
    assert await database.conn.fetchval('SELECT count(*) FROM notifications WHERE recipient_id=$1 AND class_session_id=$2', student.id, schedule) == 1
    await asyncio.gather(asyncio.to_thread(scan_upcoming_class_alerts.run), asyncio.to_thread(scan_upcoming_class_alerts.run))
    assert await database.conn.fetchval('SELECT count(*) FROM notifications WHERE recipient_id=$1 AND class_session_id=$2', student.id, schedule) == 1
    assert push.call_count == 1
