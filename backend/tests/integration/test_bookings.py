import asyncio
from datetime import timedelta

import asyncpg
import pytest

from tests.integration.factories import START

pytestmark = pytest.mark.asyncio

INSERT_ROOM = '''INSERT INTO room_reservations(room_id,reserved_by,purpose,slot_range,status)
    VALUES ($1,$2,'Constraint test',tstzrange($3,$4,'[)'),$5) RETURNING id'''


@pytest.mark.parametrize('is_lab', [False, True], ids=['room', 'lab-room'])
async def test_gist_rejects_overlap_without_service_precheck(database, is_lab):
    room, user = await database.room(is_lab), await database.user()
    conn = database.conn
    await conn.execute(INSERT_ROOM, room, user.id, START, START+timedelta(hours=1), 'pending')
    with pytest.raises(asyncpg.ExclusionViolationError) as error:
        await conn.execute(INSERT_ROOM, room, user.id, START+timedelta(minutes=30), START+timedelta(hours=2), 'approved')
    assert error.value.sqlstate == '23P01'
    # Half-open ranges allow the next class to start exactly at the boundary.
    await conn.execute(INSERT_ROOM, room, user.id, START+timedelta(hours=1), START+timedelta(hours=2), 'pending')
    # Different rooms are independent; inactive reservations don't occupy slots.
    other = await database.room(is_lab)
    await conn.execute(INSERT_ROOM, other, user.id, START, START+timedelta(hours=1), 'approved')
    for status in ('cancelled', 'rejected'):
        await conn.execute(INSERT_ROOM, room, user.id, START, START+timedelta(hours=1), status)


@pytest.mark.parametrize('is_lab', [False, True], ids=['room', 'lab-room'])
async def test_two_database_transactions_contend_on_gist(database, is_lab):
    room, user = await database.room(is_lab), await database.user()
    barrier = asyncio.Barrier(2)
    async def attempt():
        conn = await asyncpg.connect(database.dsn)
        try:
            async with conn.transaction():
                # Both transactions see the slot free before either inserts.
                assert await conn.fetchval('SELECT count(*) FROM room_reservations') == 0
                await barrier.wait()
                await conn.execute(INSERT_ROOM, room, user.id, START, START+timedelta(hours=1), 'pending')
            return 'committed'
        except (asyncpg.ExclusionViolationError, asyncpg.DeadlockDetectedError):
            # A GiST conflict can form a cycle while both inserts are pending;
            # PG aborts one transaction (40P01) instead of returning 23P01.
            return 'excluded'
        finally:
            await conn.close()
    results = await asyncio.wait_for(asyncio.gather(attempt(), attempt()), 10)
    assert sorted(results) == ['committed', 'excluded']
    assert await database.conn.fetchval('SELECT count(*) FROM room_reservations') == 1


@pytest.mark.parametrize('is_lab', [False, True], ids=['room', 'lab-room'])
async def test_two_concurrent_http_requests_one_conflict(api, database, monkeypatch, is_lab):
    from app.repositories.booking_repository import BookingRepository
    barrier = asyncio.Barrier(2)
    original = BookingRepository.create
    async def synchronized_create(self, row):
        # Force both HTTP requests past the friendly preflight SELECT. Only the
        # real DB constraint can decide the winner; no mocked database result.
        await barrier.wait()
        return await original(self, row)
    monkeypatch.setattr(BookingRepository, 'create', synchronized_create)
    room, user = await database.room(is_lab), await database.user()
    async def request():
        return await api.post('/api/v1/rooms/reservations', json=database.booking(room), headers=database.headers(user))
    results = await asyncio.wait_for(asyncio.gather(request(), request()), 10)
    assert sorted(r.status_code for r in results) == [200, 409], [r.text for r in results]
    assert await database.conn.fetchval('SELECT count(*) FROM room_reservations') == 1


@pytest.mark.xfail(strict=True, raises=pytest.fail.Exception, reason='LAB-1: lab_bench_reservations has no GiST constraint or API')
async def test_lab_bench_overlap_contract(database):
    user = await database.user()
    sql = '''INSERT INTO lab_bench_reservations(lab_name,bench_number,reserved_by,slot_range)
        VALUES ('Lab A',1,$1,tstzrange($2,$3,'[)'))'''
    await database.conn.execute(sql, user.id, START, START+timedelta(hours=1))
    with pytest.raises(asyncpg.ExclusionViolationError):
        await database.conn.execute(sql, user.id, START, START+timedelta(hours=1))


async def test_booking_approval_cancellation_and_reuse(api, database):
    student, teacher, other = await database.user(), await database.user('teacher'), await database.user()
    room = await database.room()
    headers = database.headers(student)
    payload = database.booking(room)
    first = await api.post('/api/v1/rooms/reservations', json=payload, headers=headers)
    assert first.status_code == 200, first.text
    ident = first.json()['id']
    duplicate = await api.post('/api/v1/rooms/reservations', json=payload, headers=headers)
    assert duplicate.status_code == 409
    denied = await api.post(f'/api/v1/rooms/reservations/{ident}/cancel', json={'reason':'Not mine'}, headers=database.headers(other))
    assert denied.status_code == 403
    approval = await api.post(f'/api/v1/rooms/reservations/{ident}/decide', json={'decision':'approve'}, headers=database.headers(teacher))
    assert approval.status_code == 200 and approval.json()['status'] == 'approved'
    repeated = await api.post(f'/api/v1/rooms/reservations/{ident}/decide', json={'decision':'approve'}, headers=database.headers(teacher))
    assert repeated.status_code == 409
    mine = await api.get('/api/v1/rooms/reservations', headers=headers)
    assert mine.status_code == 200 and len(mine.json()) == 1
    cancelled = await api.post(f'/api/v1/rooms/reservations/{ident}/cancel', json={'reason':'Rescheduled'}, headers=headers)
    assert cancelled.status_code == 200
    assert (await api.post('/api/v1/rooms/reservations', json=payload, headers=headers)).status_code == 200


async def test_invalid_duration_and_unknown_room(api, database):
    user = await database.user()
    room = await database.room()
    for minutes in [-1, 5, 9*60]:
        result = await api.post('/api/v1/rooms/reservations', json=database.booking(room, START, START+timedelta(minutes=minutes)), headers=database.headers(user))
        assert result.status_code == 422
    assert (await api.post('/api/v1/rooms/reservations', json=database.booking(99999), headers=database.headers(user))).status_code == 404
