"""Registration and admin approval flow, including the ER approval gap."""
import pytest

from app.models.user import UserRole
from tests.conftest import make_user

pytestmark = pytest.mark.asyncio

REGISTRATION_PASSWORD = "Passw0rd!23"


async def test_student_registration_is_active_immediately(client, db):
    response = await client.post(
        "/api/v1/auth/register/student",
        json={
            "full_name": "New Student",
            "identifier": "2029999001",
            "email": "new.student@sust.edu",
            "password": REGISTRATION_PASSWORD,
            "session_year": "22-26",
            "current_term": "3-1",
            "role": "student",
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["requires_approval"] is False

    login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "2029999001", "password": REGISTRATION_PASSWORD},
    )
    assert login.status_code == 200


async def test_teacher_registration_requires_approval(client):
    response = await client.post(
        "/api/v1/auth/register/teacher",
        json={
            "full_name": "New Teacher",
            "email": "new.teacher@sust.edu",
            "password": REGISTRATION_PASSWORD,
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["requires_approval"] is True


async def test_duplicate_email_is_rejected(client, db):
    await make_user(db, email="dupe@sust.edu")

    response = await client.post(
        "/api/v1/auth/register/student",
        json={
            "full_name": "Copycat",
            "identifier": "2029999002",
            "email": "dupe@sust.edu",
            "password": REGISTRATION_PASSWORD,
            "session_year": "22-26",
            "current_term": "3-1",
        },
    )

    assert response.status_code == 409


async def test_pending_approvals_include_er_accounts(client, db):
    """Regression: ER/LAB_ASSISTANT rows were created inactive but never
    appeared in the admin queue, so they could never be approved."""
    er = await make_user(db, role=UserRole.LAB_ASSISTANT, is_active=False)
    cr = await make_user(db, role=UserRole.CR, is_active=False)
    teacher = await make_user(db, role=UserRole.TEACHER, is_active=False)
    active_student = await make_user(db, role=UserRole.STUDENT, is_active=True)

    admin = await make_user(db, role=UserRole.SUPER_ADMIN)
    from tests.conftest import auth_header

    response = await client.get(
        "/api/v1/auth/admin/pending-approvals", headers=auth_header(admin)
    )

    assert response.status_code == 200, response.text
    pending_ids = {row["id"] for row in response.json()}

    assert str(er.id) in pending_ids
    assert str(cr.id) in pending_ids
    assert str(teacher.id) in pending_ids
    assert str(active_student.id) not in pending_ids


async def test_approved_er_can_then_log_in(client, db):
    er = await make_user(
        db,
        role=UserRole.LAB_ASSISTANT,
        identifier="er-login@sust.edu",
        password=REGISTRATION_PASSWORD,
        is_active=False,
    )
    admin = await make_user(db, role=UserRole.SUPER_ADMIN)
    from tests.conftest import auth_header

    blocked = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "er-login@sust.edu", "password": REGISTRATION_PASSWORD},
    )
    assert blocked.status_code == 401

    approve = await client.patch(f"/api/v1/auth/admin/approve/{er.id}", headers=auth_header(admin))
    assert approve.status_code == 200, approve.text

    allowed = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "er-login@sust.edu", "password": REGISTRATION_PASSWORD},
    )
    assert allowed.status_code == 200, allowed.text


async def test_pending_approvals_requires_admin(client, db):
    student = await make_user(db, role=UserRole.STUDENT)
    from tests.conftest import auth_header

    response = await client.get(
        "/api/v1/auth/admin/pending-approvals", headers=auth_header(student)
    )

    assert response.status_code == 403


async def test_approve_requires_admin(client, db):
    target = await make_user(db, is_active=False)
    student = await make_user(db, role=UserRole.STUDENT)
    from tests.conftest import auth_header

    response = await client.patch(
        f"/api/v1/auth/admin/approve/{target.id}", headers=auth_header(student)
    )

    assert response.status_code == 403
