"""Alumni registration, verification queue, and admin decisions.

The approval semantics asserted here are the ones documented in
app/services/alumni_service.py, which deliberately mirror the existing
teacher/CR/ER flow (create inactive, flip is_active on approval) rather than
inventing a separate gate.
"""
import uuid
from datetime import date

import pytest
from sqlalchemy import select

from app.core.security import get_password_hash
from app.models.alumni import AlumniProfile
from app.models.user import User, UserRole
from tests.conftest import auth_header, make_user

pytestmark = pytest.mark.asyncio

PASSWORD = "Passw0rd!23"

REGISTRATION = {
    "full_name": "Nasir Uddin",
    "email": "nasir.alumni@example.com",
    "password": PASSWORD,
    "batch_year": 2012,
    "department": "EEE",
    "graduation_date": "2016-08-15",
    "current_company": "Grameenphone",
    "designation": "Senior Engineer",
    "industry": "Telecom",
}


async def _register(client, **overrides):
    return await client.post("/api/v1/alumni/register", json={**REGISTRATION, **overrides})


def _claim_for(db, user: User, **overrides) -> AlumniProfile:
    """Persist a pending alumni claim directly, bypassing the HTTP layer."""
    fields = {
        "batch_year": 2012,
        "department": "EEE",
        "graduation_date": date(2016, 8, 15),
        "membership_status": "pending",
        "verified_by_admin": False,
        "is_visible": False,
    }
    fields.update(overrides)
    profile = AlumniProfile(user_id=user.id, **fields)
    db.add(profile)
    return profile


async def _user_by_email(db, email: str) -> User:
    return (await db.execute(select(User).where(User.email == email))).scalar_one()


async def _profile_for(db, user: User) -> AlumniProfile:
    return (
        await db.execute(select(AlumniProfile).where(AlumniProfile.user_id == user.id))
    ).scalar_one()


# --- registration ---------------------------------------------------------


async def test_alumni_registration_creates_pending_claim(client, db):
    response = await _register(client)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["requires_approval"] is True
    assert "verification" in body["message"].lower()

    user = await _user_by_email(db, REGISTRATION["email"])
    assert user.role == UserRole.ALUMNI
    # Mirrors register_teacher / register_student(CR|ER): pending means
    # inactive, so nothing authenticated is reachable before an admin approves.
    assert user.is_active is False

    profile = await _profile_for(db, user)
    assert profile.membership_status == "pending"
    assert profile.verified_by_admin is False
    # Directory visibility is a separate opt-in, never implied by approval.
    assert profile.is_visible is False
    assert profile.batch_year == 2012
    assert profile.department == "EEE"
    assert str(profile.graduation_date) == "2016-08-15"


async def test_pending_alumnus_cannot_log_in(client, db):
    """A pending alumnus must not get a session, same as a pending teacher."""
    await _register(client)

    login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": REGISTRATION["email"], "password": PASSWORD},
    )
    assert login.status_code == 401
    # And the rejection must not confirm the account exists. DomainException
    # renders as {"error": ...}; the message is deliberately the same one a
    # bad password gets, so it cannot reveal "exists but pending".
    body = login.json()
    assert "approval" not in str(body).lower()
    assert "pending" not in str(body).lower()


async def test_alumni_registration_rejects_duplicate_email(client, db):
    await make_user(db, email=REGISTRATION["email"])

    response = await _register(client)

    assert response.status_code == 409


async def test_alumni_registration_validates_claim_fields(client):
    """batch_year / department / graduation_date are required, not optional."""
    response = await client.post(
        "/api/v1/alumni/register", json={**REGISTRATION, "batch_year": 1800}
    )

    assert response.status_code == 422


# --- unauthorized access --------------------------------------------------


async def test_pending_queue_requires_authentication(client):
    response = await client.get("/api/v1/alumni/admin/pending")

    # HTTPBearer rejects a missing credential before the handler runs.
    assert response.status_code == 401


async def test_my_profile_requires_authentication(client):
    response = await client.get("/api/v1/alumni/me")

    assert response.status_code == 401


async def test_claim_requires_authentication(client):
    response = await client.post(
        "/api/v1/alumni/claim",
        json={"batch_year": 2012, "department": "EEE", "graduation_date": "2016-08-15"},
    )

    assert response.status_code == 401


# --- role protection ------------------------------------------------------


@pytest.mark.parametrize(
    "role",
    [UserRole.STUDENT, UserRole.CR, UserRole.TEACHER, UserRole.LAB_ASSISTANT, UserRole.ALUMNI],
)
async def test_non_admin_cannot_list_pending_claims(client, db, role):
    # Active, so the 403 comes from RequireRole and not from the
    # "user not active" check inside get_current_user.
    user = await make_user(db, role=role, is_active=True)

    response = await client.get("/api/v1/alumni/admin/pending", headers=auth_header(user))

    assert response.status_code == 403


async def test_non_admin_cannot_approve_claim(client, db):
    student = await make_user(db, role=UserRole.STUDENT)
    target = await make_user(db, role=UserRole.ALUMNI, is_active=False)
    profile = _claim_for(db, target)
    await db.commit()

    response = await client.patch(
        f"/api/v1/alumni/admin/approve/{profile.id}", headers=auth_header(student)
    )

    assert response.status_code == 403
    # The claim must be untouched by the refused attempt.
    await db.refresh(profile)
    assert profile.membership_status == "pending"
    await db.refresh(target)
    assert target.is_active is False


async def test_non_admin_cannot_reject_claim(client, db):
    teacher = await make_user(db, role=UserRole.TEACHER)
    target = await make_user(db, role=UserRole.ALUMNI, is_active=False)
    profile = _claim_for(db, target)
    await db.commit()

    response = await client.patch(
        f"/api/v1/alumni/admin/reject/{profile.id}", headers=auth_header(teacher)
    )

    assert response.status_code == 403


# --- admin queue ----------------------------------------------------------


async def test_admin_pending_lists_only_pending_claims(client, db):
    admin = await make_user(db, role=UserRole.SUPER_ADMIN)
    pending_user = await make_user(db, role=UserRole.ALUMNI, is_active=False)
    decided_user = await make_user(db, role=UserRole.ALUMNI, is_active=True)
    _claim_for(db, pending_user, membership_status="pending")
    _claim_for(db, decided_user, membership_status="rejected")
    await db.commit()

    response = await client.get("/api/v1/alumni/admin/pending", headers=auth_header(admin))

    assert response.status_code == 200, response.text
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["user"]["id"] == str(pending_user.id)
    assert rows[0]["membership_status"] == "pending"


# --- approval -------------------------------------------------------------


async def test_approved_claim_cannot_be_approved_again(client, db):
    admin = await make_user(db, role=UserRole.SUPER_ADMIN)
    applicant = await make_user(db, role=UserRole.ALUMNI, is_active=False)
    profile = _claim_for(db, applicant)
    await db.commit()

    first = await client.patch(
        f"/api/v1/alumni/admin/approve/{profile.id}", headers=auth_header(admin)
    )
    assert first.status_code == 200, first.text

    second = await client.patch(
        f"/api/v1/alumni/admin/approve/{profile.id}", headers=auth_header(admin)
    )
    assert second.status_code == 409


async def test_approving_unknown_claim_is_404(client, db):
    admin = await make_user(db, role=UserRole.SUPER_ADMIN)

    response = await client.patch(
        f"/api/v1/alumni/admin/approve/{uuid.uuid4()}", headers=auth_header(admin)
    )

    assert response.status_code == 404


# --- rejection ------------------------------------------------------------


async def test_admin_rejection_refuses_membership_and_keeps_account_closed(client, db):
    admin = await make_user(db, role=UserRole.SUPER_ADMIN)
    applicant = await make_user(db, role=UserRole.ALUMNI, is_active=False)
    profile = _claim_for(db, applicant)
    await db.commit()

    response = await client.patch(
        f"/api/v1/alumni/admin/reject/{profile.id}",
        json={"reason": "No matching graduation record"},
        headers=auth_header(admin),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["membership_status"] == "rejected"
    assert body["verified_by_admin"] is False

    # A rejected claimant is not a member: the account must stay closed.
    await db.refresh(applicant)
    assert applicant.is_active is False

    # And it must not sit in the queue forever.
    queue = await client.get("/api/v1/alumni/admin/pending", headers=auth_header(admin))
    assert str(profile.id) not in {row["id"] for row in queue.json()}


async def test_rejected_claim_cannot_be_approved(client, db):
    """A refusal is a decision, not a gap to be filled by a later admin."""
    admin = await make_user(db, role=UserRole.SUPER_ADMIN)
    applicant = await make_user(db, role=UserRole.ALUMNI, is_active=False)
    profile = _claim_for(db, applicant, membership_status="rejected")
    await db.commit()

    response = await client.patch(
        f"/api/v1/alumni/admin/approve/{profile.id}", headers=auth_header(admin)
    )

    assert response.status_code == 409
    await db.refresh(applicant)
    assert applicant.is_active is False


# --- claim by an existing authenticated user -----------------------------


async def test_authenticated_user_can_submit_a_claim_that_starts_pending(client, db):
    user = await make_user(db, role=UserRole.ALUMNI, is_active=True)

    response = await client.post(
        "/api/v1/alumni/claim",
        json={
            "batch_year": 2014,
            "department": "EEE (Power)",
            "graduation_date": "2018-12-20",
            "is_visible": True,
        },
        headers=auth_header(user),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["membership_status"] == "pending"
    assert body["verified_by_admin"] is False
    assert body["is_visible"] is True

    # One claim per user: a second submission is a conflict, not an update.
    again = await client.post(
        "/api/v1/alumni/claim",
        json={"batch_year": 2014, "department": "EEE (Power)", "graduation_date": "2018-12-20"},
        headers=auth_header(user),
    )
    assert again.status_code == 409


async def test_my_profile_returns_null_without_a_claim(client, db):
    user = await make_user(db, role=UserRole.ALUMNI, is_active=True)

    response = await client.get("/api/v1/alumni/me", headers=auth_header(user))

    assert response.status_code == 200
    assert response.json() is None


# --- decoupling -----------------------------------------------------------


async def test_approved_alumnus_is_active_and_can_log_in(client, db):
    """Approval is what opens the account, proven without the login path.

    The state transition is the behaviour this module owns. Whether the
    subsequent /auth/login call can be exercised here is a property of the
    shared Redis-backed throttle in app/core/rate_limit.py: that client is
    bound to whichever event loop created it first, and pytest-asyncio gives
    each test a fresh loop, so a successful login in one test poisons the
    next with "Event loop is closed". The existing test_auth.py login tests
    already cover the login path itself; this test stays on the state change
    it is actually about.
    """
    admin = await make_user(db, role=UserRole.SUPER_ADMIN)
    applicant = await make_user(db, role=UserRole.ALUMNI, is_active=False)
    profile = _claim_for(db, applicant)
    await db.commit()

    approve = await client.patch(
        f"/api/v1/alumni/admin/approve/{profile.id}", headers=auth_header(admin)
    )
    assert approve.status_code == 200, approve.text

    await db.refresh(applicant)
    assert applicant.is_active is True

    # The active alumnus can now use an ordinary authenticated route.
    me = await client.get("/api/v1/alumni/me", headers=auth_header(applicant))
    assert me.status_code == 200, me.text
    assert me.json()["membership_status"] == "active"


async def test_login_flow_activates_only_after_approval(client, db):
    """End-to-end: a pending alumnus is refused, then allowed once approved.

    Uses the throttle's public entry point to release the cached Redis client
    before logging in, so this test does not inherit the shared-loop problem
    described in test_approved_alumnus_is_active_and_can_log_in.
    """
    from app.core import rate_limit

    rate_limit._redis = None

    admin = await make_user(db, role=UserRole.SUPER_ADMIN)
    applicant = await make_user(
        db,
        role=UserRole.ALUMNI,
        identifier="alum-e2e@sust.edu",
        email="alum-e2e@sust.edu",
        password=PASSWORD,
        is_active=False,
    )
    profile = _claim_for(db, applicant)
    await db.commit()

    blocked = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "alum-e2e@sust.edu", "password": PASSWORD},
    )
    assert blocked.status_code == 401, blocked.text

    approve = await client.patch(
        f"/api/v1/alumni/admin/approve/{profile.id}", headers=auth_header(admin)
    )
    assert approve.status_code == 200, approve.text

    rate_limit._redis = None
    allowed = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "alum-e2e@sust.edu", "password": PASSWORD},
    )
    assert allowed.status_code == 200, allowed.text
