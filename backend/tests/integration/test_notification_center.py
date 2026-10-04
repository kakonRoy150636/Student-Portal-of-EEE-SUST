import asyncio
import json
import uuid
from unittest.mock import AsyncMock

import pytest

from app.api.v1.endpoints.notifications import notification_events
from app.services.notification_service import NotificationService

pytestmark = pytest.mark.asyncio


async def create(database, user):
    async with database.sessions() as db, db.begin():
        await NotificationService(db).enqueue(user.id, uuid.uuid4(), 'class_reminder', 'low')


async def test_mark_read_and_unregister_are_user_scoped(api, database):
    first, second = await database.user(), await database.user()
    await create(database, first)
    await create(database, second)
    ident = await database.conn.fetchval('SELECT id FROM notifications WHERE recipient_id=$1', first.id)
    other = database.headers(second)
    assert (await api.patch(f'/api/v1/notifications/{ident}/read', headers=other)).status_code == 404
    own = database.headers(first)
    response = await api.get('/api/v1/notifications/summary', headers=own)
    assert response.json()['unread_count'] == 1
    assert response.json()['items'][0]['data_payload']['url'] == '/schedule'
    assert (await api.patch(f'/api/v1/notifications/{ident}/read', headers=own)).json()['is_read'] is True
    assert (await api.get('/api/v1/notifications/summary', headers=own)).json()['unread_count'] == 0
    assert (await api.get('/api/v1/notifications/summary', headers=other)).json()['unread_count'] == 1
    registration = await api.post('/api/v1/notifications/devices/register', headers=own, json={'fcm_token':'test-token'})
    device = registration.json()['device_id']
    assert (await api.delete(f'/api/v1/notifications/devices/{device}', headers=other)).status_code == 204
    assert await database.conn.fetchval('SELECT count(*) FROM device_tokens') == 1
    assert (await api.delete(f'/api/v1/notifications/devices/{device}', headers=own)).status_code == 204
    assert await database.conn.fetchval('SELECT count(*) FROM device_tokens') == 0


async def test_live_feed_updates_without_exposing_other_users(database, monkeypatch):
    first, second = await database.user(), await database.user()
    await create(database, second)
    request = AsyncMock()
    request.is_disconnected.return_value = False
    async def no_wait(_):
        pass
    monkeypatch.setattr(asyncio, 'sleep', no_wait)
    events = notification_events(request, first.id, database.sessions)
    initial = await anext(events)
    assert json.loads(initial.split('data: ',1)[1]) == {'items':[], 'unread_count':0}
    await create(database, first)
    update = json.loads((await anext(events)).split('data: ',1)[1])
    assert len(update['items']) == update['unread_count'] == 1
    assert await anext(events) == ': heartbeat\n\n'
    request.is_disconnected.return_value = True
    with pytest.raises(StopAsyncIteration):
        await anext(events)


async def test_read_all_and_stream_require_auth(api, database):
    first, second = await database.user(), await database.user()
    await create(database, first)
    await create(database, second)
    assert (await api.patch('/api/v1/notifications/read-all', headers=database.headers(first))).status_code == 200
    assert await database.conn.fetchval('SELECT count(*) FROM notifications WHERE is_read=false') == 1
    assert (await api.get('/api/v1/notifications/stream')).status_code == 401
    assert (await api.patch('/api/v1/notifications/read-all')).status_code == 401


async def test_stream_http_headers_and_unread_total_beyond_inbox_limit(api, database, monkeypatch):
    from app.api.v1.endpoints import notifications as endpoints
    user = await database.user()
    await database.conn.execute("""
        INSERT INTO notifications (recipient_id,title,body)
        SELECT $1,'Portal update','Open the portal for details.' FROM generate_series(1,103)
    """, user.id)
    headers = database.headers(user)
    snapshot = (await api.get('/api/v1/notifications/summary', headers=headers)).json()
    assert snapshot['unread_count'] == 103 and len(snapshot['items']) == 100
    original = endpoints.notification_events
    async def one_event(request, user_id, sessions):
        events = original(request, user_id, database.sessions)
        try:
            yield await anext(events)
        finally:
            await events.aclose()
    monkeypatch.setattr(endpoints, 'notification_events', one_event)
    response = await api.get('/api/v1/notifications/stream', headers=headers)
    assert response.status_code == 200
    assert response.headers['content-type'].startswith('text/event-stream')
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['x-accel-buffering'] == 'no'
    assert json.loads(response.text.split('data: ',1)[1])['unread_count'] == 103
