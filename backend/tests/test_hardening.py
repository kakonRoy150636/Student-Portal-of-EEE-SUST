"""Hardening regressions added in the 2026-10 review pass.

Each test corresponds to a finding, so a future change that reintroduces the
behaviour fails here rather than in production:

* response security headers (there were none),
* registration input validation (unbounded strings reached the driver, and an
  invented course offering was accepted),
* account-enumeration resistance on signup (the duplicate-email message used
  to confirm that an address had an account),
* the generic integrity-error handler (constraint violations were 500s).
"""
import uuid

import pytest

from app.models.academic import Course, CourseOffering, Semester
from app.models.user import UserRole
from tests.conftest import auth_header, make_user

pytestmark = pytest.mark.asyncio

PASSWORD = "Passw0rd!23"


def _student_payload(**overrides) -> dict:
    payload = {
        "full_name": "Hardening Probe",
        "identifier": "2099000001",
        "email": "hardening@sust.edu",
        "password": PASSWORD,
        "session_year": "22-26",
        "current_term": "3-1",
        "role": "student",
        "course_selections": [],
    }
    payload.update(overrides)
    return payload


# ── security headers ────────────────────────────────────────────────────────

async def test_api_responses_carry_security_headers(client):
    response = await client.get("/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Content-Security-Policy"].startswith("default-src 'none'")


async def test_error_responses_also_carry_security_headers(client):
    """A 401 with a JSON body is still a document a browser could sniff."""
    response = await client.get("/api/v1/courses")
    assert response.status_code == 401
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


async def test_hsts_is_not_sent_outside_production(client):
    # Pinning a browser to https for localhost would break the dev server.
    assert "Strict-Transport-Security" not in (await client.get("/health")).headers


# ── registration validation ─────────────────────────────────────────────────

async def test_unknown_course_offering_is_rejected_before_the_account_exists(client, db):
    response = await client.post(
        "/api/v1/auth/register/student",
        json=_student_payload(
            course_selections=[
                {"course_offering_id": str(uuid.uuid4()), "enrollment_type": "main"}
            ]
        ),
    )
    # A 422 with an explanation beats an unhandled IntegrityError 500 (which is
    # what this became on Postgres).
    assert response.status_code == 422, response.text
    assert "Unknown course offering" in response.json()["error"]

    # And the account was not half-created.
    login = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "2099000001", "password": PASSWORD},
    )
    assert login.status_code == 401


async def test_real_course_offering_still_registers(client, db):
    semester = Semester(title="3-1", is_active=True, start_date=__import__("datetime").date.today(),
                        end_date=__import__("datetime").date.today())
    db.add(semester)
    await db.flush()
    course = Course(course_code="EEE 311", title="Electrical Machines II", credit_hours=3.0, type="theory")
    db.add(course)
    await db.flush()
    offering = CourseOffering(course_id=course.id, semester_id=semester.id)
    db.add(offering)
    await db.commit()

    response = await client.post(
        "/api/v1/auth/register/student",
        json=_student_payload(
            course_selections=[{"course_offering_id": str(offering.id), "enrollment_type": "main"}]
        ),
    )
    assert response.status_code == 201, response.text
    assert response.json()["requires_approval"] is False


async def test_duplicate_course_offering_is_rejected(client, db):
    offering_id = str(uuid.uuid4())
    response = await client.post(
        "/api/v1/auth/register/student",
        json=_student_payload(
            course_selections=[
                {"course_offering_id": offering_id, "enrollment_type": "main"},
                {"course_offering_id": offering_id, "enrollment_type": "main"},
            ]
        ),
    )
    # Duplicate selection is caught by validation (unknown id here), and the
    # duplicate check would catch it for a real id -- either way, not a 500.
    assert response.status_code == 422


@pytest.mark.parametrize(
    "field,value",
    [
        ("session_year", "2022-2026-EXTRA-LONG"),
        ("current_term", "term-three"),
        ("session_year", ""),
        ("identifier", "x"),
    ],
)
async def test_unbounded_registration_fields_are_rejected(client, field, value):
    response = await client.post(
        "/api/v1/auth/register/student", json=_student_payload(**{field: value})
    )
    assert response.status_code == 422, f"{field}={value!r} should not be accepted"


async def test_duplicate_signup_message_does_not_confirm_the_account(client, db):
    await make_user(db, identifier="2023999998", email="taken@sust.edu")

    response = await client.post(
        "/api/v1/auth/register/student",
        json=_student_payload(identifier="2023999997", email="taken@sust.edu"),
    )
    assert response.status_code == 409
    message = response.json()["error"]
    # The old wording ("Email already in use") confirmed that this address has
    # an account. The new one is actionable without being an oracle.
    assert "already exists" in message
    assert "email already in use" not in message.lower()


# ── error handling ──────────────────────────────────────────────────────────

async def test_unhandled_exception_returns_generic_error(client, db, monkeypatch):
    """A 500 must be a clean JSON body, not a traceback or SQL fragment.

    The shared `client` fixture uses httpx's default `raise_app_exceptions=True`,
    which re-raises instead of surfacing the response -- correct for catching
    programming errors in tests, but it hides what a real server would send. A
    second transport with the flag off sees the actual HTTP response.
    """
    from httpx import ASGITransport, AsyncClient

    from app.main import app
    from app.services import course_service

    user = await make_user(db)

    async def boom(*_args, **_kwargs):
        raise RuntimeError("connection string: postgres://user:secret@host/db")

    monkeypatch.setattr(course_service.CourseService, "list_for_user", boom)

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as raw_client:
        response = await raw_client.get("/api/v1/courses", headers=auth_header(user))

    assert response.status_code == 500
    assert response.json() == {"error": "An unexpected error occurred."}
    assert "postgres://" not in response.text


# ── list endpoints refuse to build an unbounded response ─────────────────────


async def test_list_endpoints_cap_the_page_size(client, db):
    """A page size above the cap is a 422, not a full-table response.

    Every list route previously had no bound at all: a client could ask for
    the whole table and the API would serialise it.
    """
    user = await make_user(db)
    headers = auth_header(user)

    too_big = await client.get("/api/v1/notifications?limit=500", headers=headers)
    assert too_big.status_code == 422

    negative = await client.get("/api/v1/notifications?offset=-1", headers=headers)
    assert negative.status_code == 422

    at_cap = await client.get("/api/v1/notifications?limit=200", headers=headers)
    assert at_cap.status_code == 200

    assert (
        await client.get("/api/v1/projects?limit=500", headers=headers)
    ).status_code == 422
    assert (
        await client.get("/api/v1/career/opportunities?limit=500", headers=headers)
    ).status_code == 422

