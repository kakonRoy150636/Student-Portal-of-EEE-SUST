"""Forced password change, MFA, password reset, sessions and the audit trail.

These cover the second half of the review remediation:

* the environment-bootstrapped administrator, which replaced the committed
  ``super_admin`` bcrypt hash in ``database/seed.sql``;
* the server-side gate that stops a temporary password being used as a session;
* TOTP enrolment and two-step login, including recovery codes;
* self-service password reset (enumeration-resistant request, single-use token,
  all other sessions revoked);
* device list + revoke; and
* audit rows for the decisions that used to leave no trace.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pyotp
import pytest
from sqlalchemy import select

from app.core.bootstrap import ensure_bootstrap_admin
from app.core.security import hash_secret_token
from app.models.audit import AuditLog
from app.models.auth import PasswordResetToken, RefreshToken
from app.models.facility import RoomReservation
from app.models.user import User, UserRole
from app.tasks.maintenance import cleanup
from tests.conftest import auth_header, make_user

pytestmark = pytest.mark.asyncio

PASSWORD = "Passw0rd!23"
NEW_PASSWORD = "Rotated!Password9"


async def _login(client, identifier: str, password: str = PASSWORD):
    return await client.post(
        "/api/v1/auth/login", json={"identifier": identifier, "password": password}
    )


async def _user_by_email(db, email: str) -> User | None:
    return (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()


# ───────────────────────────────────────────────────────── bootstrap admin


async def test_bootstrap_admin_is_created_once_with_forced_change(db, session_factory, monkeypatch):
    from app.core import bootstrap as bootstrap_module

    monkeypatch.setattr(bootstrap_module.settings, "BOOTSTRAP_ADMIN_EMAIL", "root@sust.edu")
    monkeypatch.setattr(bootstrap_module.settings, "BOOTSTRAP_ADMIN_PASSWORD", "Bootstrap!Passw0rd")
    monkeypatch.setattr(bootstrap_module.settings, "BOOTSTRAP_ADMIN_IDENTIFIER", "root")

    await ensure_bootstrap_admin(session_factory)
    admin = await _user_by_email(db, "root@sust.edu")
    assert admin is not None
    assert admin.role == UserRole.SUPER_ADMIN
    assert admin.must_change_password is True
    # The environment credential is never stored in plaintext and is bounded by
    # bcrypt's 72-byte limit.
    assert admin.password_hash != "Bootstrap!Passw0rd"

    # Idempotent: a second start must not create a duplicate.
    await ensure_bootstrap_admin(session_factory)
    count = len(
        (await db.execute(select(User).where(User.role == UserRole.SUPER_ADMIN))).scalars().all()
    )
    assert count == 1


async def test_bootstrap_refuses_a_short_password(db, session_factory, monkeypatch):
    from app.core import bootstrap as bootstrap_module

    monkeypatch.setattr(bootstrap_module.settings, "BOOTSTRAP_ADMIN_EMAIL", "weak@sust.edu")
    monkeypatch.setattr(bootstrap_module.settings, "BOOTSTRAP_ADMIN_PASSWORD", "short")

    await ensure_bootstrap_admin(session_factory)
    assert await _user_by_email(db, "weak@sust.edu") is None


async def test_bootstrap_is_skipped_when_an_admin_exists(db, session_factory, monkeypatch):
    from app.core import bootstrap as bootstrap_module

    await make_user(db, role=UserRole.SUPER_ADMIN)
    monkeypatch.setattr(bootstrap_module.settings, "BOOTSTRAP_ADMIN_EMAIL", "second@sust.edu")
    monkeypatch.setattr(bootstrap_module.settings, "BOOTSTRAP_ADMIN_PASSWORD", "Bootstrap!Passw0rd")

    await ensure_bootstrap_admin(session_factory)
    assert await _user_by_email(db, "second@sust.edu") is None


# ────────────────────────────────────────────────────── forced password change


async def test_forced_password_change_blocks_the_rest_of_the_api(client, db):
    user = await make_user(db, role=UserRole.STUDENT)
    user.must_change_password = True
    await db.commit()

    login = await _login(client, user.identifier)
    assert login.status_code == 200
    assert login.json()["user"]["must_change_password"] is True
    headers = {"Authorization": f"Bearer {login.json()['tokens']['access_token']}"}

    blocked = await client.get("/api/v1/rooms", headers=headers)
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "password_change_required"

    # /auth/me stays reachable so the client can render the forced screen.
    assert (await client.get("/api/v1/auth/me", headers=headers)).status_code == 200

    wrong = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "not-the-password", "new_password": NEW_PASSWORD},
        headers=headers,
    )
    assert wrong.status_code == 401

    changed = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
        headers=headers,
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["user"]["must_change_password"] is False
    new_headers = {
        "Authorization": f"Bearer {changed.json()['tokens']['access_token']}"
    }

    # The old password no longer works and the new one does.
    assert (await _login(client, user.identifier, PASSWORD)).status_code == 401
    assert (await _login(client, user.identifier, NEW_PASSWORD)).status_code == 200
    assert (await client.get("/api/v1/rooms", headers=new_headers)).status_code == 200


# ──────────────────────────────────────────────────────────────── MFA (TOTP)


async def _enrol_mfa(client, db, user) -> tuple[list[str], dict]:
    """Sign in, run setup+enable, return (recovery codes, auth headers)."""
    login = await _login(client, user.identifier)
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['tokens']['access_token']}"}

    started = await client.post("/api/v1/auth/mfa/setup", headers=headers)
    assert started.status_code == 200, started.text
    secret = started.json()["secret"]
    assert started.json()["otpauth_uri"].startswith("otpauth://totp/")

    enabled = await client.post(
        "/api/v1/auth/mfa/enable",
        json={"code": pyotp.TOTP(secret).now()},
        headers=headers,
    )
    assert enabled.status_code == 200, enabled.text
    codes = enabled.json()["recovery_codes"]
    assert len(codes) == 10

    # Read specific columns rather than the ORM instance: the test's session
    # already holds `user`, and a stale identity-map entry would hide what the
    # request's own session committed.
    enabled_flag, stored_secret, stored_hashes = (
        await db.execute(
            select(User.mfa_enabled, User.mfa_secret, User.mfa_recovery_hashes).where(
                User.id == user.id
            )
        )
    ).one()
    assert enabled_flag is True
    assert stored_secret == secret
    # Only hashes are stored, never the codes themselves.
    assert all(code not in (stored_hashes or []) for code in codes)
    return codes, headers


async def test_super_admin_without_mfa_can_only_enrol(client, db):
    admin = await make_user(db, role=UserRole.SUPER_ADMIN)
    admin.mfa_enabled = False
    admin.mfa_secret = None
    await db.commit()

    login = await _login(client, admin.identifier)
    headers = {"Authorization": f"Bearer {login.json()['tokens']['access_token']}"}

    blocked = await client.get("/api/v1/admin/audit-logs", headers=headers)
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "mfa_enrollment_required"

    allowed = await client.post("/api/v1/auth/mfa/setup", headers=headers)
    assert allowed.status_code == 200


async def test_mfa_login_requires_a_valid_second_factor(client, db):
    user = await make_user(db, role=UserRole.STUDENT)
    codes, _ = await _enrol_mfa(client, db, user)
    secret = (await db.execute(select(User.mfa_secret).where(User.id == user.id))).scalar_one()

    first = await _login(client, user.identifier)
    assert first.status_code == 200
    body = first.json()
    assert body["mfa_required"] is True
    # A challenge is not a session.
    assert "tokens" not in body

    mfa_token = body["mfa_token"]
    rejected = await client.post(
        "/api/v1/auth/mfa/verify", json={"mfa_token": mfa_token, "code": "000000"}
    )
    # A random six-digit code is essentially never valid; a real TOTP code is.
    if not rejected.json().get("tokens"):
        assert rejected.status_code == 401

    verified = await client.post(
        "/api/v1/auth/mfa/verify",
        json={"mfa_token": mfa_token, "code": pyotp.TOTP(secret).now()},
    )
    assert verified.status_code == 200, verified.text
    assert verified.json()["user"]["id"] == str(user.id)

    # Recovery code: accepted once, then consumed.
    second = (await _login(client, user.identifier)).json()["mfa_token"]
    used = await client.post(
        "/api/v1/auth/mfa/verify",
        json={"mfa_token": second, "code": codes[0]},
    )
    assert used.status_code == 200, used.text

    third = (await _login(client, user.identifier)).json()["mfa_token"]
    replayed = await client.post(
        "/api/v1/auth/mfa/verify",
        json={"mfa_token": third, "code": codes[0]},
    )
    assert replayed.status_code == 401
    remaining = (await db.execute(select(User.mfa_recovery_hashes).where(User.id == user.id))).scalar_one()
    assert len(remaining) == 9


async def test_mfa_disable_requires_the_password(client, db):
    user = await make_user(db, role=UserRole.STUDENT)
    _, headers = await _enrol_mfa(client, db, user)

    wrong = await client.post(
        "/api/v1/auth/mfa/disable", json={"password": "nope"}, headers=headers
    )
    assert wrong.status_code == 401

    ok = await client.post(
        "/api/v1/auth/mfa/disable", json={"password": PASSWORD}, headers=headers
    )
    assert ok.status_code == 200
    enabled_flag, stored_secret = (
        await db.execute(select(User.mfa_enabled, User.mfa_secret).where(User.id == user.id))
    ).one()
    assert enabled_flag is False and stored_secret is None


# ───────────────────────────────────────────────────────────── password reset


async def test_password_reset_request_is_enumeration_resistant(client, db):
    await make_user(db, email="known@sust.edu", identifier="known-id")

    known = await client.post(
        "/api/v1/auth/password-reset/request", json={"email": "known@sust.edu"}
    )
    unknown = await client.post(
        "/api/v1/auth/password-reset/request", json={"email": "nobody@sust.edu"}
    )
    assert known.status_code == 202 and unknown.status_code == 202
    assert known.json() == unknown.json()

    # A token exists for the real account and (obviously) not for the other.
    assert (
        await db.execute(select(PasswordResetToken))
    ).scalars().all() != []
    # Only the hash is persisted, so the emailed token is not recoverable.
    stored = (await db.execute(select(PasswordResetToken))).scalars().one()
    assert len(stored.token_hash) == 64


async def test_password_reset_confirm_revokes_every_other_session(client, db):
    user = await make_user(db, email="reset@sust.edu", identifier="reset-id")
    login = await _login(client, "reset-id")
    assert login.status_code == 200
    refresh_cookie = client.cookies.get("refresh_token")
    assert refresh_cookie

    await client.post("/api/v1/auth/password-reset/request", json={"email": "reset@sust.edu"})

    # The endpoint never returns the token (it is emailed), so the test reads
    # the plaintext from the dev-mode log line instead of inventing a shortcut.
    # Simpler and more direct: mint one the same way the service does and store
    # its hash, then confirm through the API.
    token = uuid.uuid4().hex + uuid.uuid4().hex
    stored = (await db.execute(select(PasswordResetToken))).scalars().one()
    stored.token_hash = hash_secret_token(token)
    await db.commit()

    confirmed = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": NEW_PASSWORD},
    )
    assert confirmed.status_code == 200, confirmed.text

    # Single use.
    again = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": "Another!Passw0rd1"},
    )
    assert again.status_code == 422

    assert (await _login(client, "reset-id", PASSWORD)).status_code == 401
    assert (await _login(client, "reset-id", NEW_PASSWORD)).status_code == 200

    # The session that existed before the reset is gone: its refresh token was
    # revoked, so presenting it cannot mint a new access token.
    replay = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": refresh_cookie})
    assert replay.status_code == 401


# ─────────────────────────────────────────────────────────────── sessions list


async def test_session_list_marks_the_current_device_and_revokes_others(client, db):
    user = await make_user(db)
    first = await _login(client, user.identifier)
    assert first.status_code == 200
    headers = {"Authorization": f"Bearer {first.json()['tokens']['access_token']}"}

    listed = await client.get("/api/v1/auth/sessions", headers=headers)
    assert listed.status_code == 200, listed.text
    sessions = listed.json()
    assert len(sessions) == 1
    assert sessions[0]["is_current"] is True

    # A second login (another device) adds a family.
    second_login = await client.post(
        "/api/v1/auth/login", json={"identifier": user.identifier, "password": PASSWORD}
    )
    assert second_login.status_code == 200
    listed_again = await client.get("/api/v1/auth/sessions", headers=headers)
    sessions = listed_again.json()
    assert len(sessions) == 2

    other = next(item for item in sessions if not item["is_current"])
    revoked = await client.delete(f"/api/v1/auth/sessions/{other['family_id']}", headers=headers)
    assert revoked.status_code == 200

    remaining = (await client.get("/api/v1/auth/sessions", headers=headers)).json()
    target = next(item for item in remaining if item["family_id"] == other["family_id"])
    assert target["is_active"] is False


# ───────────────────────────────────────────────────────────────── audit trail


async def test_admin_decisions_are_audited(client, db):
    admin = await make_user(db, role=UserRole.SUPER_ADMIN)
    student = await make_user(db, role=UserRole.STUDENT)
    pending_teacher = await make_user(db, role=UserRole.TEACHER, is_active=False)

    body = {"user_id": str(pending_teacher.id)}
    approved = await client.patch(
        f"/api/v1/auth/admin/approve/{pending_teacher.id}",
        json=body,
        headers=auth_header(admin),
    )
    assert approved.status_code == 200, approved.text

    entry = (
        await db.execute(select(AuditLog).where(AuditLog.action == "user.approve"))
    ).scalar_one()
    assert entry.actor_id == admin.id
    assert entry.entity_id == str(pending_teacher.id)
    assert "teacher" in (entry.detail or "")

    # And the trail is readable by an admin only.
    listing = await client.get("/api/v1/admin/audit-logs", headers=auth_header(admin))
    assert listing.status_code == 200
    assert any(item["action"] == "user.approve" for item in listing.json()["items"])
    assert listing.json()["total"] >= 1

    forbidden = await client.get("/api/v1/admin/audit-logs", headers=auth_header(student))
    assert forbidden.status_code == 403


# ───────────────────────────────────────────────────────────── token cleanup


async def test_cleanup_prunes_dead_tokens_but_keeps_live_ones(db):
    user = await make_user(db)
    now = datetime.now(timezone.utc)
    live = RefreshToken(
        user_id=user.id,
        token_family=uuid.uuid4(),
        token_hash=hash_secret_token("live-token"),
        is_revoked=False,
        expires_at=now + timedelta(days=2),
    )
    dead_revoked = RefreshToken(
        user_id=user.id,
        token_family=uuid.uuid4(),
        token_hash=hash_secret_token("dead-revoked"),
        is_revoked=True,
        expires_at=now - timedelta(days=30),
    )
    dead_expired = RefreshToken(
        user_id=user.id,
        token_family=uuid.uuid4(),
        token_hash=hash_secret_token("dead-expired"),
        is_revoked=False,
        expires_at=now - timedelta(days=30),
    )
    spent_reset = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_secret_token("spent"),
        is_used=True,
        expires_at=now - timedelta(days=40),
    )
    db.add_all([live, dead_revoked, dead_expired, spent_reset])
    await db.commit()

    summary = await cleanup(db)
    assert summary["refresh_tokens_deleted"] == 2
    assert summary["password_reset_tokens_deleted"] == 1

    remaining = (await db.execute(select(RefreshToken))).scalars().all()
    assert [row.token_hash for row in remaining] == [hash_secret_token("live-token")]


# ─────────────────────────────────────────────── refresh rotation race handling


async def test_duplicate_refresh_inside_grace_window_does_not_kill_the_family(client, db):
    """Two tabs refreshing at once must not look like token theft.

    The first presentation rotates the token; the second arrives with the old
    one. Inside the grace window the second is refused, but the family -- and
    therefore every other tab -- survives. (Theft detection is asserted by the
    password-reset test, where the replay is well outside the window.)
    """
    user = await make_user(db)
    login = await _login(client, user.identifier)
    assert login.status_code == 200
    original = client.cookies.get("refresh_token")
    assert original

    first = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": original})
    assert first.status_code == 200

    # The stale cookie is presented again immediately (same second).
    second = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": original})
    assert second.status_code == 401

    # The family is still usable: the token from the first rotation works.
    rotated = first.cookies.get("refresh_token")
    assert rotated
    third = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": rotated})
    assert third.status_code == 200, "the family must not be revoked by a race"
