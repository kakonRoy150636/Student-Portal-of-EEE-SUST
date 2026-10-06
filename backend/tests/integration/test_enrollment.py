import uuid

import pytest

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize('credits,expected', [
    pytest.param([3,3,3,3,1.5], 422, marks=pytest.mark.xfail(strict=True, raises=AssertionError, reason='ENR-1: minimum 15 credits not implemented')),
    ([3]*5, 201),
    ([3]*8, 201),
    pytest.param([3]*8+[1.5], 422, marks=pytest.mark.xfail(strict=True, raises=AssertionError, reason='ENR-2: maximum 24 credits not implemented')),
], ids=['13.5-below-minimum', '15-inclusive', '24-inclusive', '25.5-above-maximum'])
async def test_registration_credit_boundaries(api, database, credits, expected):
    semester = await database.semester()
    offerings = [await database.offering(c, semester=semester, published=True) for c in credits]
    payload = database.registration(offerings)
    result = await api.post('/api/v1/auth/register/student', json=payload)
    assert result.status_code == expected, result.text
    count = await database.conn.fetchval('''SELECT count(*) FROM course_enrollments e
        JOIN users u ON u.id=e.student_id WHERE u.identifier=$1''', payload['identifier'])
    assert count == (len(offerings) if expected == 201 else 0)


@pytest.mark.parametrize('duplicate', [False, True])
async def test_invalid_enrollment_is_atomic(api, database, duplicate):
    offering = await database.offering()
    payload = database.registration([offering, offering if duplicate else uuid.uuid4()])
    result = await api.post('/api/v1/auth/register/student', json=payload)
    assert result.status_code == 422
    assert await database.conn.fetchval('SELECT count(*) FROM users WHERE identifier=$1', payload['identifier']) == 0
    assert await database.conn.fetchval('SELECT count(*) FROM course_enrollments') == 0


async def test_prerequisite_policy_not_yet_testable():
    # Deliberately no invented model/API or fake validator. No prerequisite
    # relationship/completion record exists to arrange unmet vs met scenarios.
    pytest.xfail('ENR-3: prerequisite storage/completion policy and enforcement do not exist; behavior test blocked')
