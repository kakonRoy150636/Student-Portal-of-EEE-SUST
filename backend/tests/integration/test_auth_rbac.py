import asyncio
import uuid

import pytest

from app.core.security import hash_secret_token
from tests.integration.factories import PASSWORD

pytestmark = pytest.mark.asyncio


async def login(api, user):
    result = await api.post('/api/v1/auth/login', json={'identifier': user.identifier, 'password': PASSWORD})
    assert result.status_code == 200, result.text
    return result


async def test_rotation_replay_revokes_only_affected_family(api, database):
    user = await database.user()
    first = await login(api, user)
    stolen = first.cookies['refresh_token']
    api.cookies.clear()
    refreshed = await api.post('/api/v1/auth/refresh', headers={'Cookie': 'refresh_token='+stolen})
    assert refreshed.status_code == 200, refreshed.text
    current = refreshed.cookies['refresh_token']
    assert current != stolen
    row = await database.conn.fetchrow('SELECT * FROM refresh_tokens WHERE token_hash=$1', hash_secret_token(stolen))
    assert row['is_revoked']
    assert row['token_hash'] != stolen
    independent = (await login(api, user)).cookies['refresh_token']
    api.cookies.clear()
    replay = await api.post('/api/v1/auth/refresh', headers={'Cookie': 'refresh_token='+stolen})
    assert replay.status_code == 401
    live = await database.conn.fetchval('SELECT count(*) FROM refresh_tokens WHERE token_family=$1 AND NOT is_revoked', row['token_family'])
    assert live == 0
    assert (await api.post('/api/v1/auth/refresh', headers={'Cookie': 'refresh_token='+current})).status_code == 401
    assert (await api.post('/api/v1/auth/refresh', headers={'Cookie': 'refresh_token='+independent})).status_code == 200


async def test_simultaneous_refresh_requests_do_not_leave_live_descendant(api, database):
    user = await database.user()
    token = (await login(api, user)).cookies['refresh_token']
    api.cookies.clear()
    async def refresh():
        return await api.post('/api/v1/auth/refresh', headers={'Cookie': 'refresh_token='+token})
    responses = await asyncio.wait_for(asyncio.gather(refresh(), refresh()), 10)
    assert sorted(r.status_code for r in responses) == [200, 401]
    assert await database.conn.fetchval('SELECT count(*) FROM refresh_tokens WHERE NOT is_revoked') == 0


async def test_expired_token_and_logout(api, database):
    user = await database.user()
    token = (await login(api, user)).cookies['refresh_token']
    await database.conn.execute("UPDATE refresh_tokens SET expires_at=now()-interval '1 second'")
    assert (await api.post('/api/v1/auth/refresh')).status_code == 401
    await login(api, user)
    assert (await api.post('/api/v1/auth/logout')).status_code == 200
    assert await database.conn.fetchval('SELECT count(*) FROM refresh_tokens WHERE NOT is_revoked') == 0


async def test_student_rejected_by_privileged_routes(api, database):
    teacher, student = await database.user('teacher'), await database.user()
    offering = await database.offering(teacher=teacher)
    headers = database.headers(student)
    routes = [
        ('GET','/auth/admin/pending-approvals',None),
        ('PATCH',f'/auth/admin/approve/{student.id}',None),
        ('GET','/alumni/admin/pending',None),
        ('PATCH',f'/alumni/admin/approve/{uuid.uuid4()}',None),
        ('PATCH',f'/alumni/admin/reject/{uuid.uuid4()}',{}),
        ('POST','/alumni/events',{}),
        ('POST','/alumni/scholarships',{}),
        ('GET','/rooms/reservations/all',None),
        ('POST',f'/rooms/reservations/{uuid.uuid4()}/decide',{'decision':'approve'}),
        ('GET','/labs/equipment',None),
        ('GET',f'/attendance/courses/{offering}/summary',None),
        ('POST','/attendance/sessions',{'course_offering_id':str(offering),'session_date':'2030-01-07','records':[]}),
    ]
    for method, path, payload in routes:
        result = await api.request(method, '/api/v1'+path, json=payload, headers=headers)
        assert result.status_code == 403, (path, result.text)
    assert await database.conn.fetchval('SELECT count(*) FROM attendance_sessions') == 0


async def test_teacher_assignment_and_admin_access(api, database):
    teacher, stranger, admin = await database.user('teacher'), await database.user('teacher'), await database.user('super_admin')
    offering = await database.offering(teacher=teacher)
    for user, status in [(teacher,200), (stranger,403), (admin,200)]:
        result = await api.get(f'/api/v1/attendance/courses/{offering}/summary', headers=database.headers(user))
        assert result.status_code == status, result.text


async def test_real_redis_stops_login_before_password_verification(api, database, monkeypatch, real_redis):
    from app.services import auth_service
    from unittest.mock import AsyncMock
    # Valid JSON but nonexistent account avoids spending bcrypt for first 30.
    # The old failure delay is separately tested; avoid sleeping for minutes.
    monkeypatch.setattr(auth_service, 'verify_attempt', AsyncMock(return_value=0))
    for _ in range(30):
        result = await api.post('/api/v1/auth/login', json={'identifier': 'absent-account', 'password': PASSWORD})
        assert result.status_code == 401
    authenticate = AsyncMock(side_effect=AssertionError('Rate limiter must run first'))
    monkeypatch.setattr(auth_service.AuthService, 'authenticate', authenticate)
    result = await api.post('/api/v1/auth/login', json={'identifier': 'absent-account', 'password': PASSWORD})
    assert result.status_code == 429 and int(result.headers['Retry-After']) > 0
    authenticate.assert_not_awaited()
    assert await real_redis.keys('portal:limit:login:*')
