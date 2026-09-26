"""Room booking service and route tests."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models.facility import Room
from app.models.user import UserRole
from tests.conftest import make_user, auth_header

pytestmark = pytest.mark.asyncio

SLOT_START = datetime(2030, 1, 1, 10, 0, tzinfo=timezone.utc)
SLOT_END = SLOT_START + timedelta(hours=1)


async def _make_room(db, room_number="Room 999", capacity=30) -> Room:
    room = Room(room_number=room_number, building="Test", capacity=capacity, is_lab=False)
    db.add(room)
    await db.commit()
    await db.refresh(room)
    return room


def _payload(room: Room, start=SLOT_START, end=SLOT_END) -> dict:
    return {
        "room_id": room.id,
        "purpose": "Study session",
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
    }


async def test_booking_requires_authentication(pg_client, pg_db):
    room = await _make_room(pg_db)

    response = await pg_client.post("/api/v1/rooms/reservations", json=_payload(room))

    assert response.status_code == 401


async def test_create_booking_returns_pending(pg_client, pg_db):
    room = await _make_room(pg_db)
    student = await make_user(pg_db, role=UserRole.STUDENT)

    response = await pg_client.post(
        "/api/v1/rooms/reservations", json=_payload(room), headers=auth_header(student)
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "pending"


async def test_overlapping_booking_is_rejected(pg_client, pg_db):
    """The SQLite test DB has no GiST exclusion constraint, so the friendly
    pre-flight overlap check in the service is what rejects this."""
    room = await _make_room(pg_db)
    student = await make_user(pg_db, role=UserRole.STUDENT)
    headers = auth_header(student)

    first = await pg_client.post("/api/v1/rooms/reservations", json=_payload(room), headers=headers)
    assert first.status_code == 200, first.text

    second = await pg_client.post(
        "/api/v1/rooms/reservations",
        json=_payload(room, SLOT_START + timedelta(minutes=30), SLOT_END + timedelta(minutes=30)),
        headers=headers,
    )

    assert second.status_code == 409, second.text


async def test_booking_validation_rejects_bad_ranges(client, db):
    room = await _make_room(db)
    student = await make_user(db, role=UserRole.STUDENT)
    headers = auth_header(student)

    # end before start
    backwards = await client.post(
        "/api/v1/rooms/reservations",
        json=_payload(room, SLOT_END, SLOT_START),
        headers=headers,
    )
    assert backwards.status_code == 422

    # longer than 8 hours
    too_long = await client.post(
        "/api/v1/rooms/reservations",
        json=_payload(room, SLOT_START, SLOT_START + timedelta(hours=9)),
        headers=headers,
    )
    assert too_long.status_code == 422

    # shorter than 15 minutes
    too_short = await client.post(
        "/api/v1/rooms/reservations",
        json=_payload(room, SLOT_START, SLOT_START + timedelta(minutes=5)),
        headers=headers,
    )
    assert too_short.status_code == 422


async def test_cancel_requires_owner_or_staff(pg_client, pg_db):
    room = await _make_room(pg_db)
    owner = await make_user(pg_db, role=UserRole.STUDENT)
    stranger = await make_user(pg_db, role=UserRole.STUDENT)

    created = await pg_client.post(
        "/api/v1/rooms/reservations", json=_payload(room), headers=auth_header(owner)
    )
    reservation_id = created.json()["id"]

    denied = await pg_client.post(
        f"/api/v1/rooms/reservations/{reservation_id}/cancel",
        json={"reason": "not mine"},
        headers=auth_header(stranger),
    )
    assert denied.status_code == 403

    allowed = await pg_client.post(
        f"/api/v1/rooms/reservations/{reservation_id}/cancel",
        json={"reason": "changed plans"},
        headers=auth_header(owner),
    )
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["status"] == "cancelled"


async def test_students_cannot_decide_reservations(pg_client, pg_db):
    room = await _make_room(pg_db)
    student = await make_user(pg_db, role=UserRole.STUDENT)

    created = await pg_client.post(
        "/api/v1/rooms/reservations", json=_payload(room), headers=auth_header(student)
    )
    reservation_id = created.json()["id"]

    response = await pg_client.post(
        f"/api/v1/rooms/reservations/{reservation_id}/decide",
        json={"decision": "approve"},
        headers=auth_header(student),
    )

    assert response.status_code == 403


async def test_teacher_can_approve_booking(pg_client, pg_db):
    room = await _make_room(pg_db)
    student = await make_user(pg_db, role=UserRole.STUDENT)
    teacher = await make_user(pg_db, role=UserRole.TEACHER)

    created = await pg_client.post(
        "/api/v1/rooms/reservations", json=_payload(room), headers=auth_header(student)
    )
    reservation_id = created.json()["id"]

    response = await pg_client.post(
        f"/api/v1/rooms/reservations/{reservation_id}/decide",
        json={"decision": "approve", "reason": None},
        headers=auth_header(teacher),
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "approved"


async def test_all_reservations_is_staff_only(pg_client, pg_db):
    student = await make_user(pg_db, role=UserRole.STUDENT)
    teacher = await make_user(pg_db, role=UserRole.TEACHER)

    denied = await pg_client.get("/api/v1/rooms/reservations/all", headers=auth_header(student))
    assert denied.status_code == 403

    allowed = await pg_client.get("/api/v1/rooms/reservations/all", headers=auth_header(teacher))
    assert allowed.status_code == 200, allowed.text
