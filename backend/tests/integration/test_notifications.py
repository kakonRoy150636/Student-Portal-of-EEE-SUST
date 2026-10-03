import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from app.services.notification_service import NotificationService
from app.services.notification_scanner import scan_classes, group_digest
from app.services.notification_dispatch import deliver_batch
from app.integrations.firebase_client import InvalidDeviceToken, RetryableFCMError, AmbiguousFCMError, PermanentFCMError

pytestmark = pytest.mark.asyncio
NOW = datetime(2030, 1, 7, 9, 55, tzinfo=timezone.utc)  # Monday 15:55 Dhaka


async def register(database, user, token='test-device'):
    async with database.sessions() as db:
        return await NotificationService(db).register_device(user.id, token)


async def enqueue(database, user, priority='high', type_='announcement', event=None, now=NOW):
    async with database.sessions() as db, db.begin():
        return await NotificationService(db).enqueue(user.id, event or uuid.uuid4(), type_, priority, now)


async def scan(database, now=NOW):
    async with database.sessions() as db, db.begin():
        return await scan_classes(db, now)


async def digest(database, now=NOW+timedelta(minutes=6)):
    async with database.sessions() as db, db.begin():
        return await group_digest(db, now)


async def arrange(database):
    teacher, student = await database.user('teacher'), await database.user()
    offering = await database.offering(teacher=teacher)
    await database.enroll(student, offering)
    schedule = await database.schedule(offering, teacher, await database.room())
    await register(database, student)
    return student, schedule


async def test_scanner_concurrency_occurrence_identity_and_index(database):
    student, schedule = await arrange(database)
    results = await asyncio.wait_for(asyncio.gather(scan(database), scan(database)), 10)
    assert sum(count for count, _ in results) == 1
    assert (await scan(database))[0] == 0
    assert await database.conn.fetchval('SELECT count(*) FROM notification_log') == 1
    assert await database.conn.fetchval('SELECT count(*) FROM notifications') == 1
    assert (await scan(database, NOW+timedelta(days=7)))[0] == 1
    assert await database.conn.fetchval('SELECT count(DISTINCT event_id) FROM notification_log') == 2
    index_names = {r[0] for r in await database.conn.fetch("SELECT indexname FROM pg_indexes WHERE schemaname='public'")}
    assert {'ix_class_schedules_day_start','ix_course_enrollments_notification_recipients','ix_notification_log_pending'} <= index_names
    rows = await database.conn.fetch('SELECT title,body,data_payload FROM notifications')
    assert all(student.full_name not in r['body'] and student.email not in r['body'] for r in rows)
    assert 'grade' not in str(rows).lower()


async def test_scanner_ignores_inactive_user_and_outside_window(database):
    student, _ = await arrange(database)
    assert (await scan(database, NOW-timedelta(minutes=20)))[0] == 0
    await database.conn.execute('UPDATE users SET is_active=false WHERE id=$1', student.id)
    assert (await scan(database))[0] == 0


async def test_scanner_crosses_dhaka_midnight(database):
    _, schedule = await arrange(database)
    await database.conn.execute("UPDATE class_schedules SET day_of_week='Tuesday',start_time='00:05',end_time='01:00' WHERE id=$1", schedule)
    monday_night = NOW.replace(hour=17, minute=59)  # 23:59 Monday locally
    assert (await scan(database, monday_night))[0] == 1
    assert (await scan(database, monday_night+timedelta(minutes=2)))[0] == 0


async def test_high_priority_immediate_task_and_concurrent_dispatch(database, monkeypatch):
    from app.core.config import settings
    from app.tasks import notifications as tasks
    student = await database.user()
    await register(database, student)
    monkeypatch.setattr(settings, 'DATABASE_URL', database.dsn.replace('postgresql://','postgresql+asyncpg://'))
    published = Mock()
    monkeypatch.setattr(tasks.deliver_notification, 'delay', published)
    event = uuid.uuid4()
    await asyncio.to_thread(tasks.create_notification.run, str(student.id), str(event), 'announcement', 'high')
    await asyncio.to_thread(tasks.create_notification.run, str(student.id), str(event), 'announcement', 'high')
    published.assert_called_once()
    batch = uuid.UUID(published.call_args.args[0])
    sender = Mock(return_value='fcm-message-id')
    await asyncio.wait_for(asyncio.gather(
        deliver_batch(database.sessions, batch, NOW, sender),
        deliver_batch(database.sessions, batch, NOW, sender),
    ), 10)
    assert sender.call_count == 1
    assert sender.call_args.kwargs['priority'] == 'high'
    await deliver_batch(database.sessions, batch, NOW+timedelta(minutes=6), sender)
    assert sender.call_count == 1


async def test_device_registration_upsert_and_preferences_are_user_scoped(api, database):
    student, other = await database.user(), await database.user()
    header = database.headers(student)
    for _ in range(2):
        result = await api.post('/api/v1/notifications/devices/register', headers=header,
                                json={'fcm_token':'opaque-token','platform':'web'})
        assert result.status_code == 200, result.text
    assert await database.conn.fetchval('SELECT count(*) FROM device_tokens') == 1
    assert await database.conn.fetchval('SELECT last_seen IS NOT NULL FROM device_tokens')
    payload = {'per_type':{'class_reminder':{'push':False,'in_app':True}}, 'quiet_start':'22:00','quiet_end':'07:00'}
    result = await api.put('/api/v1/notifications/preferences', headers=header, json=payload)
    assert result.status_code == 200, result.text
    read = await api.get('/api/v1/notifications/preferences', headers=header)
    assert read.json()['timezone'] == 'Asia/Dhaka'
    assert read.json()['per_type']['class_reminder']['push'] is False
    other_read = await api.get('/api/v1/notifications/preferences', headers=database.headers(other))
    assert other_read.json()['per_type']['class_reminder']['push'] is True
    assert (await api.get('/api/v1/notifications/preferences')).status_code == 401
    assert (await api.put('/api/v1/notifications/preferences', headers=header, json={'quiet_start':'22:00'})).status_code == 422
    assert (await api.put('/api/v1/notifications/preferences', headers=header, json={'per_type':{'grades':{'push':True}}})).status_code == 422


async def test_preferences_low_priority_and_readback(api, database):
    user = await database.user()
    await register(database, user)
    headers = database.headers(user)
    await api.put('/api/v1/notifications/preferences', headers=headers, json={'per_type':{'announcement':{'push':False,'in_app':False}}})
    assert (await enqueue(database, user))[1] is None
    assert await database.conn.fetchval('SELECT count(*) FROM notifications') == 0
    await api.put('/api/v1/notifications/preferences', headers=headers, json={'per_type':{'announcement':{'push':True,'in_app':True}}})
    assert (await enqueue(database, user, priority='low'))[1] is None
    assert await database.conn.fetchval('SELECT count(*) FROM notification_batches') == 0
    inbox = await api.get('/api/v1/notifications', headers=headers)
    assert inbox.status_code == 200 and len(inbox.json()) == 1
    assert inbox.json()[0]['title'] == 'Portal update'


async def test_push_without_in_app_and_quiet_medium_digest(api, database):
    user = await database.user()
    await register(database, user)
    headers = database.headers(user)
    await api.put('/api/v1/notifications/preferences', headers=headers, json={
        'per_type':{'announcement':{'push':True,'in_app':False}},
        'quiet_start':'15:00', 'quiet_end':'17:00',
    })
    _, high = await enqueue(database, user)
    await enqueue(database, user, priority='medium')
    assert await database.conn.fetchval('SELECT count(*) FROM notifications') == 0
    assert await digest(database) == []  # still inside 15:00–17:00 Dhaka
    sender = Mock(return_value='fcm-id')
    end = NOW.replace(hour=11, minute=0)  # 17:00 Dhaka
    await deliver_batch(database.sessions, high, end, sender)
    batches = await digest(database, end)
    assert len(batches) == 1
    await deliver_batch(database.sessions, batches[0], end, sender)
    assert sender.call_count == 2


async def test_quiet_hours_defer_high_and_preference_rechecked(api, database):
    user = await database.user()
    await register(database, user)
    headers = database.headers(user)
    await api.put('/api/v1/notifications/preferences', headers=headers, json={'quiet_start':'22:00','quiet_end':'07:00'})
    late = NOW.replace(hour=17)  # 23:55 Dhaka
    _, batch = await enqueue(database, user, now=late)
    due = await database.conn.fetchval('SELECT due_at FROM notification_batches WHERE id=$1', batch)
    assert due == (late+timedelta(days=1)).replace(hour=1,minute=0)
    sender = Mock(return_value='fcm-id')
    await deliver_batch(database.sessions, batch, late, sender)
    sender.assert_not_called()
    assert await database.conn.fetchval('SELECT count(*) FROM notifications') == 1
    await api.put('/api/v1/notifications/preferences', headers=headers, json={'per_type':{'announcement':{'push':False,'in_app':True}}})
    await deliver_batch(database.sessions, batch, due, sender)
    sender.assert_not_called()
    assert await database.conn.fetchval('SELECT status FROM notification_deliveries') == 'suppressed'


async def test_medium_digest_groups_by_user_and_type(database):
    user, other = await database.user(), await database.user()
    await register(database, user)
    await register(database, other, 'other-device')
    for who, type_ in [(user,'announcement'),(user,'announcement'),(user,'lab_reminder'),(other,'announcement')]:
        assert (await enqueue(database, who, priority='medium', type_=type_))[1] is None
    assert await digest(database, NOW) == []
    groups = await asyncio.gather(digest(database), digest(database))
    batches = [ident for group in groups for ident in group]
    assert len(batches) == 3
    assert await digest(database) == []
    sender = Mock(return_value='fcm-id')
    for ident in batches:
        await deliver_batch(database.sessions, ident, NOW+timedelta(minutes=6), sender)
    assert sender.call_count == 3
    assert any('2 new announcement' in call.args[2] for call in sender.call_args_list)
    assert all(call.kwargs['priority'] == 'normal' for call in sender.call_args_list)


@pytest.mark.parametrize('error,expected,remaining', [
    (InvalidDeviceToken('invalid'),'invalid',0),
    (AmbiguousFCMError('timeout'),'unknown',1),
    (PermanentFCMError('payload'),'failed',1),
])
async def test_delivery_failure_classification(database, error, expected, remaining):
    user = await database.user()
    await register(database, user)
    _, batch = await enqueue(database, user)
    sender = Mock(side_effect=error)
    await deliver_batch(database.sessions, batch, NOW, sender)
    await deliver_batch(database.sessions, batch, NOW+timedelta(hours=1), sender)
    assert sender.call_count == 1
    assert await database.conn.fetchval('SELECT status FROM notification_deliveries') == expected
    assert await database.conn.fetchval('SELECT count(*) FROM device_tokens') == remaining


async def test_retry_backoff_never_resends_successful_devices(database):
    user = await database.user()
    await register(database, user, 'good')
    await register(database, user, 'retry')
    _, batch = await enqueue(database, user)
    calls = []
    def sender(token, *args, **kwargs):
        calls.append(token)
        if token == 'retry' and calls.count(token) < 3:
            raise RetryableFCMError('quota')
        return 'fcm-id'
    with pytest.raises(RetryableFCMError):
        await deliver_batch(database.sessions, batch, NOW, sender)
    retry_at = await database.conn.fetchval("SELECT next_attempt_at FROM notification_deliveries WHERE status='pending'")
    assert retry_at == NOW+timedelta(seconds=60)
    await deliver_batch(database.sessions, batch, NOW+timedelta(seconds=59), sender)
    with pytest.raises(RetryableFCMError):
        await deliver_batch(database.sessions, batch, retry_at, sender)
    retry_at = await database.conn.fetchval("SELECT next_attempt_at FROM notification_deliveries WHERE status='pending'")
    assert retry_at == NOW+timedelta(seconds=180)
    await deliver_batch(database.sessions, batch, retry_at, sender)
    assert calls.count('good') == 1 and calls.count('retry') == 3
    assert await database.conn.fetchval("SELECT count(*) FROM notification_deliveries WHERE status='sent'") == 2


async def test_interrupted_delivery_is_not_resent(database):
    user = await database.user()
    await register(database, user)
    _, batch = await enqueue(database, user)
    await database.conn.execute("UPDATE notification_deliveries SET status='inflight',attempted_at=$1", NOW)
    sender = Mock()
    await deliver_batch(database.sessions, batch, NOW+timedelta(minutes=6), sender)
    sender.assert_not_called()
    assert await database.conn.fetchval('SELECT status FROM notification_deliveries') == 'unknown'


async def test_retry_attempts_are_bounded(database):
    user = await database.user()
    await register(database, user)
    _, batch = await enqueue(database, user)
    sender = Mock(side_effect=RetryableFCMError('temporary'))
    at = NOW
    for attempt in range(1, 7):
        if attempt < 6:
            with pytest.raises(RetryableFCMError):
                await deliver_batch(database.sessions, batch, at, sender)
            at = await database.conn.fetchval('SELECT next_attempt_at FROM notification_deliveries')
        else:
            await deliver_batch(database.sessions, batch, at, sender)
    await deliver_batch(database.sessions, batch, at+timedelta(days=1), sender)
    assert sender.call_count == 6
    assert await database.conn.fetchval('SELECT status FROM notification_deliveries') == 'failed'


async def test_outbox_recovers_commit_before_broker_failure(database, monkeypatch):
    from app.core.config import settings
    from app.tasks import notifications as tasks
    user = await database.user()
    await register(database, user)
    monkeypatch.setattr(settings, 'DATABASE_URL', database.dsn.replace('postgresql://','postgresql+asyncpg://'))
    publish = Mock(side_effect=RuntimeError('broker unavailable'))
    monkeypatch.setattr(tasks.deliver_notification, 'delay', publish)
    with pytest.raises(RuntimeError):
        await asyncio.to_thread(tasks.create_notification.run, str(user.id), str(uuid.uuid4()), 'announcement', 'high')
    assert await database.conn.fetchval('SELECT count(*) FROM notification_log') == 1
    publish.side_effect = None
    result = await asyncio.to_thread(tasks.recover_pending_notifications.run)
    assert result['queued'] == 1


async def test_notification_content_rejects_unknown_types(database):
    user = await database.user()
    with pytest.raises(ValueError):
        await enqueue(database, user, type_='grade:95 student:someone')
    assert await database.conn.fetchval('SELECT count(*) FROM notification_log') == 0
