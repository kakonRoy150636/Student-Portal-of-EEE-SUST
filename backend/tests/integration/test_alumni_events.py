import pytest


pytestmark = pytest.mark.asyncio


async def test_finite_event_capacity_assigns_seats_and_rejects_overbooking(api, database):
    admin = await database.user(role="super_admin")
    first = await database.user()
    second = await database.user()
    event = await api.post(
        "/api/v1/alumni/events",
        headers=database.headers(admin),
        json={
            "title": "Capacity test",
            "description": "A finite capacity event",
            "venue": "EEE Lab",
            "starts_at": "2030-01-07T10:00:00Z",
            "ends_at": "2030-01-07T12:00:00Z",
            "capacity": 1,
            "is_published": True,
        },
    )
    assert event.status_code == 201, event.text
    event_id = event.json()["id"]

    first_rsvp = await api.post(
        f"/api/v1/alumni/events/{event_id}/rsvp",
        headers=database.headers(first),
        json={"rsvp_status": "attending"},
    )
    assert first_rsvp.status_code == 200, first_rsvp.text
    assert await database.conn.fetchval(
        "SELECT lower(slot_range) FROM event_rsvps WHERE event_id=$1 AND user_id=$2",
        event_id,
        first.id,
    ) == 1

    second_rsvp = await api.post(
        f"/api/v1/alumni/events/{event_id}/rsvp",
        headers=database.headers(second),
        json={"rsvp_status": "attending"},
    )
    assert second_rsvp.status_code == 409, second_rsvp.text
