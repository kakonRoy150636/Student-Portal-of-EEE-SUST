"""Auth endpoint tests: login, refresh rotation, reuse detection, role gating."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.security import create_access_token, hash_secret_token
from app.main import app
from app.models.auth import RefreshToken
from app.models.user import UserRole
from tests.conftest import make_user, auth_header

pytestmark = pytest.mark.asyncio

STUDENT_PASSWORD = "Passw0rd!23"


async def test_login_issues_access_token_and_refresh_cookie(client, db):
    await make_user(db, role=UserRole.STUDENT, identifier="2023338049", password=STUDENT_PASSWORD)

    response = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "2023338049", "password": STUDENT_PASSWORD},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["user"]["identifier"] == "2023338049"
    assert body["tokens"]["token_type"] == "Bearer"
    assert body["tokens"]["access_token"]

    # The refresh token must be a cookie, never part of the JSON body.
    assert "refresh_token" not in body["tokens"]
    assert "refresh_token" in response.cookies


async def test_login_accepts_email_as_identifier(client, db):
    email = "kakon@student.sust.edu"
    await make_user(db, identifier="2023338049", email=email, password=STUDENT_PASSWORD)

    response = await client.post(
        "/api/v1/auth/login", json={"identifier": email, "password": STUDENT_PASSWORD}
    )

    assert response.status_code == 200, response.text
    assert response.json()["user"]["email"] == email


async def test_login_accepts_long_email(client, db):
    """Regression: identifier was capped at 32 chars while emails are 255."""
    email = "a.very.long.institutional.address@student.sust.edu.bd"
    assert len(email) > 32
    await make_user(db, email=email, password=STUDENT_PASSWORD)

    response = await client.post(
        "/api/v1/auth/login", json={"identifier": email, "password": STUDENT_PASSWORD}
    )

    assert response.status_code == 200, response.text


async def test_login_rejects_bad_password(client, db):
    await make_user(db, identifier="2023338050", password=STUDENT_PASSWORD)

    response = await client.post(
        "/api/v1/auth/login", json={"identifier": "2023338050", "password": "WrongPass1!"}
    )

    assert response.status_code == 401


async def test_login_overlong_password_is_401_not_500(client, db):
    """bcrypt raises above 72 bytes; auth must fail cleanly, not 500."""
    await make_user(db, identifier="2023338051", password=STUDENT_PASSWORD)

    response = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "2023338051", "password": "x" * 200},
    )

    assert response.status_code == 401


async def test_inactive_student_cannot_log_in(client, db):
    await make_user(db, identifier="2023338052", password=STUDENT_PASSWORD, is_active=False)

    response = await client.post(
        "/api/v1/auth/login", json={"identifier": "2023338052", "password": STUDENT_PASSWORD}
    )

    assert response.status_code == 401


async def test_refresh_rotates_and_revokes_old_token(client, db):
    user = await make_user(db, identifier="2023338053", password=STUDENT_PASSWORD)

    login = await client.post(
        "/api/v1/auth/login", json={"identifier": "2023338053", "password": STUDENT_PASSWORD}
    )
    first_access = login.json()["tokens"]["access_token"]
    first_refresh = login.cookies["refresh_token"]

    refreshed = await client.post("/api/v1/auth/refresh")

    assert refreshed.status_code == 200, refreshed.text
    # The new access token is only *guaranteed* to differ once the iat/exp
    # second ticks over -- both are stamped at whole-second resolution, so a
    # rotation inside the same second legitimately yields an identical string.
    # The refresh token is the real signal that rotation happened.
    new_access = refreshed.json()["tokens"]["access_token"]
    assert isinstance(new_access, str) and new_access
    new_refresh = refreshed.cookies["refresh_token"]
    assert new_refresh != first_refresh

    # The rotated-out token must be marked revoked in the store.
    from sqlalchemy import select

    stored = (
        await db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == hash_secret_token(first_refresh))
        )
    ).scalar_one()
    assert stored.is_revoked is True


async def test_reusing_a_rotated_refresh_token_revokes_the_whole_family(client, db):
    """Theft detection: replaying a rotated token must kill the family."""
    user = await make_user(db, identifier="2023338054", password=STUDENT_PASSWORD)

    login = await client.post(
        "/api/v1/auth/login", json={"identifier": "2023338054", "password": STUDENT_PASSWORD}
    )
    stolen = login.cookies["refresh_token"]

    # Legitimate rotation.
    first_refresh = await client.post("/api/v1/auth/refresh")
    assert first_refresh.status_code == 200
    live_cookie = first_refresh.cookies["refresh_token"]

    # Attacker replays the stolen token from a separate client that holds only
    # the stolen cookie -- it must not share the legitimate client's jar.
    attacker = AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies={"refresh_token": stolen},
    )
    async with attacker:
        replay = await attacker.post("/api/v1/auth/refresh")
    assert replay.status_code == 401

    # The now-legitimate session must be dead too: the family was revoked.
    from sqlalchemy import select

    rows = (
        await db.execute(
            select(RefreshToken).where(RefreshToken.user_id == user.id)
        )
    ).scalars().all()
    assert rows, "expected stored refresh tokens"
    assert all(row.is_revoked for row in rows)

    # And the live cookie is now worthless.
    second = await client.post("/api/v1/auth/refresh")
    assert second.status_code == 401


async def test_refresh_without_cookie_is_401(client):
    response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 401


async def test_logout_revokes_refresh_token(client, db):
    await make_user(db, identifier="2023338055", password=STUDENT_PASSWORD)
    await client.post(
        "/api/v1/auth/login", json={"identifier": "2023338055", "password": STUDENT_PASSWORD}
    )

    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 200

    after = await client.post("/api/v1/auth/refresh")
    assert after.status_code == 401


async def test_me_requires_valid_token(client, db):
    user = await make_user(db, identifier="2023338056", password=STUDENT_PASSWORD)

    ok = await client.get("/api/v1/auth/me", headers=auth_header(user))
    assert ok.status_code == 200
    assert ok.json()["identifier"] == "2023338056"

    missing = await client.get("/api/v1/auth/me")
    assert missing.status_code == 401


async def test_non_uuid_sub_is_401_not_500(client):
    """Regression: an unparsable sub used to raise ValueError -> 500."""
    token = create_access_token({"sub": "not-a-uuid", "role": "student"})

    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


async def test_inactive_user_token_is_rejected(client, db):
    user = await make_user(db, identifier="2023338057", is_active=False)

    response = await client.get("/api/v1/auth/me", headers=auth_header(user))

    assert response.status_code == 401
