"""Security regressions: avatar auth, enumeration, attendance IDOR, throttle."""
import uuid
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, create_upload_token
from app.models.academic import Course, CourseOffering, CourseOfferingTeacher, Semester
from app.models.attendance import AttendanceSession
from app.models.user import UserRole
from tests.conftest import auth_header, make_user

pytestmark = pytest.mark.asyncio

PASSWORD = "Passw0rd!23"


def _upload_header(user) -> dict:
    return {"Authorization": f"Bearer {create_upload_token(str(user.id))}"}


async def test_avatar_upload_requires_authentication(client):
    response = await client.post(
        "/api/v1/auth/avatar-upload", params={"filename": "photo.jpg"}
    )
    assert response.status_code == 401


async def test_avatar_upload_rejects_refresh_token_type(client, db):
    user = await make_user(db)
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    # A refresh-shaped JWT must not be tradable for a write primitive.
    from datetime import datetime, timedelta, timezone
    import jwt
    from app.core.config import settings

    refresh = jwt.encode(
        {
            "sub": str(user.id),
            "exp": datetime.now(timezone.utc) + timedelta(days=1),
            "iat": datetime.now(timezone.utc),
            "type": "refresh",
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    response = await client.post(
        "/api/v1/auth/avatar-upload",
        params={"filename": "photo.jpg"},
        headers={"Authorization": f"Bearer {refresh}"},
    )
    assert response.status_code == 401
    # Sanity: a real access token is accepted far enough to reach storage.
    accepted = await client.post(
        "/api/v1/auth/avatar-upload",
        params={"filename": "not-an-image.txt"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert accepted.status_code == 415


async def test_pending_account_can_use_upload_token_but_not_access_token(client, db):
    pending = await make_user(db, role=UserRole.TEACHER, is_active=False)

    blocked = await client.post(
        "/api/v1/auth/avatar-upload",
        params={"filename": "photo.jpg"},
        headers=auth_header(pending),
    )
    assert blocked.status_code == 401

    allowed = await client.post(
        "/api/v1/auth/avatar-upload",
        params={"filename": "not-an-image.txt"},
        headers=_upload_header(pending),
    )
    # 415 means the token was accepted and the extension check ran.
    assert allowed.status_code == 415


async def test_finalize_rejects_another_users_key(client, db):
    owner = await make_user(db)
    attacker = await make_user(db)

    response = await client.post(
        "/api/v1/auth/avatar-upload/finalize",
        json={"file_key": f"avatars/{owner.id}-{uuid.uuid4()}.jpg"},
        headers=auth_header(attacker),
    )
    assert response.status_code == 403


async def test_register_returns_upload_token_and_ignores_client_avatar_key(client):
    response = await client.post(
        "/api/v1/auth/register/student",
        json={
            "full_name": "Photo Student",
            "identifier": "2029999111",
            "email": "photo.student@sust.edu",
            "password": PASSWORD,
            "session_year": "22-26",
            "current_term": "3-1",
            "role": "student",
            "avatar_key": "avatars/someone-else.jpg",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["upload_token"]
    login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "2029999111", "password": PASSWORD},
    )
    assert login.status_code == 200
    assert login.json()["user"]["avatar_key"] is None


async def test_pending_and_unknown_login_share_the_same_message(client, db):
    await make_user(
        db,
        role=UserRole.TEACHER,
        identifier="pending-teacher@sust.edu",
        password=PASSWORD,
        is_active=False,
    )

    pending = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "pending-teacher@sust.edu", "password": PASSWORD},
    )
    unknown = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "ghost_xyz_notreal", "password": PASSWORD},
    )
    assert pending.status_code == 401
    assert unknown.status_code == 401
    assert pending.json() == unknown.json()


async def _seed_session(db: AsyncSession, teacher) -> AttendanceSession:
    semester = Semester(
        title=f"T{uuid.uuid4().hex[:6]}",
        is_active=True,
        start_date=date(2030, 1, 1),
        end_date=date(2030, 6, 1),
    )
    db.add(semester)
    await db.flush()
    course = Course(
        course_code=f"EEE{uuid.uuid4().hex[:4].upper()}",
        title="Signals",
        credit_hours=3.0,
        type="theory",
    )
    db.add(course)
    await db.flush()
    offering = CourseOffering(
        course_id=course.id, semester_id=semester.id, coordinator_id=teacher.id
    )
    db.add(offering)
    await db.flush()
    db.add(CourseOfferingTeacher(course_offering_id=offering.id, teacher_id=teacher.id))
    session = AttendanceSession(
        course_offering_id=offering.id,
        taken_by=teacher.id,
        topic_discussed="intro",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def test_student_cannot_rewrite_attendance(client, db):
    teacher = await make_user(db, role=UserRole.TEACHER)
    student = await make_user(db, role=UserRole.STUDENT)
    session = await _seed_session(db, teacher)

    response = await client.put(
        f"/api/v1/attendance/sessions/{session.id}",
        json={"records": [{"student_id": str(student.id), "status": "present"}]},
        headers=auth_header(student),
    )
    assert response.status_code == 403


async def test_unknown_attendance_session_is_404(client, db):
    teacher = await make_user(db, role=UserRole.TEACHER)
    response = await client.put(
        f"/api/v1/attendance/sessions/{uuid.uuid4()}",
        json={"records": []},
        headers=auth_header(teacher),
    )
    assert response.status_code == 404


async def test_assigned_teacher_can_update_attendance(client, db):
    teacher = await make_user(db, role=UserRole.TEACHER)
    session = await _seed_session(db, teacher)
    response = await client.put(
        f"/api/v1/attendance/sessions/{session.id}",
        json={"records": []},
        headers=auth_header(teacher),
    )
    assert response.status_code == 200, response.text


class _FakeRedis:
    def __init__(self):
        self.store: dict[str, str] = {}

    async def get(self, key):
        return self.store.get(key)

    async def incr(self, key):
        self.store[key] = str(int(self.store.get(key) or 0) + 1)
        return int(self.store[key])

    async def expire(self, key, _ttl):
        return True

    async def delete(self, key):
        self.store.pop(key, None)

    def pipeline(self):
        return _FakePipe(self)


class _FakePipe:
    def __init__(self, redis: _FakeRedis):
        self.redis = redis
        self.ops: list[tuple] = []

    def incr(self, key):
        self.ops.append(("incr", key))

    def expire(self, key, ttl):
        self.ops.append(("expire", key, ttl))

    async def execute(self):
        results = []
        for op in self.ops:
            if op[0] == "incr":
                results.append(await self.redis.incr(op[1]))
            elif op[0] == "expire":
                results.append(await self.redis.expire(op[1], op[2]))
        self.ops.clear()
        return results


async def test_throttle_uses_both_counters_and_spares_correct_passwords():
    """A spray must pay the IP counter; a correct password must not wait."""
    from app.core import rate_limit

    fake = _FakeRedis()
    slept: list[int] = []

    async def _capture(seconds):
        slept.append(seconds)

    with patch.object(rate_limit, "_redis", fake), patch(
        "app.core.rate_limit.asyncio.sleep", new=AsyncMock(side_effect=_capture)
    ):
        # Four free failures against one account, then the schedule starts.
        for _ in range(rate_limit.ACCOUNT_GRACE_FAILURES):
            waited = await rate_limit.verify_attempt("one-id", False, "1.1.1.1")
            assert waited == 0
        waited = await rate_limit.verify_attempt("one-id", False, "1.1.1.1")
        assert waited == 1
        assert slept == [1]

        # A spray across many identifiers from one IP must eventually trip
        # the IP counter even though no single account ever exceeds grace.
        slept.clear()
        spray_ip = "9.9.9.9"
        for i in range(rate_limit.IP_GRACE_FAILURES):
            waited = await rate_limit.verify_attempt(f"spray-{i}", False, spray_ip)
            assert waited == 0
        waited = await rate_limit.verify_attempt("spray-last", False, spray_ip)
        assert waited == 1

        # A correct password must never wait, even after earlier failures.
        slept.clear()
        waited = await rate_limit.verify_attempt("one-id", True, "1.1.1.1")
        assert waited == 0
        assert slept == []
