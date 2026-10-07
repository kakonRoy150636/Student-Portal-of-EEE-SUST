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
    offering = await database.offering(published=True)
    payload = database.registration([offering, offering if duplicate else uuid.uuid4()])
    result = await api.post('/api/v1/auth/register/student', json=payload)
    assert result.status_code == 422
    assert await database.conn.fetchval('SELECT count(*) FROM users WHERE identifier=$1', payload['identifier']) == 0
    assert await database.conn.fetchval('SELECT count(*) FROM course_enrollments') == 0


@pytest.mark.parametrize("role,stored_role", [("student", "student"), ("cr", "cr"), ("er", "lab_assistant")])
@pytest.mark.parametrize("with_selections", [False, True])
async def test_registration_roles_and_legacy_selection_types_remain_compatible(
    api, database, role, stored_role, with_selections,
):
    semester = await database.semester()
    offerings = [await database.offering(3, semester=semester, published=True) for _ in range(3)] if with_selections else []
    payload = database.registration(offerings)
    payload["role"] = role
    if with_selections:
        payload["course_selections"][1]["enrollment_type"] = "drop"
        payload["course_selections"][2]["enrollment_type"] = "improvement"

    result = await api.post("/api/v1/auth/register/student", json=payload)
    assert result.status_code == 201, result.text
    assert result.json()["requires_approval"] == (role != "student")
    user = await database.conn.fetchrow("SELECT id,role,is_active FROM users WHERE identifier=$1", payload["identifier"])
    assert user["role"] == stored_role
    assert user["is_active"] == (role == "student")
    assert await database.conn.fetchval("SELECT count(*) FROM profiles_student WHERE user_id=$1", user["id"]) == 1
    rows = await database.conn.fetch("SELECT course_offering_id,status FROM course_enrollments WHERE student_id=$1", user["id"])
    assert {row["course_offering_id"]: row["status"] for row in rows} == (
        dict(zip(offerings, ["main", "drop", "improvement"])) if with_selections else {}
    )


@pytest.mark.parametrize("unavailable", ["draft", "inactive"])
async def test_registration_rejects_unavailable_offerings_without_partial_account(api, database, unavailable):
    semester = await database.semester()
    offering = await database.offering(semester=semester, published=unavailable != "draft")
    if unavailable == "inactive":
        await database.conn.execute("UPDATE semesters SET is_active=false WHERE id=$1", semester)
    payload = database.registration([offering])

    result = await api.post("/api/v1/auth/register/student", json=payload)
    assert result.status_code == 422, result.text
    for table in ("users", "profiles_student", "course_enrollments", "notification_log", "notifications"):
        assert await database.conn.fetchval(f"SELECT count(*) FROM {table}") == 0


async def test_prerequisite_policy_not_yet_testable():
    # Deliberately no invented model/API or fake validator. No prerequisite
    # relationship/completion record exists to arrange unmet vs met scenarios.
    pytest.xfail('ENR-3: prerequisite storage/completion policy and enforcement do not exist; behavior test blocked')
