from datetime import date

import pytest
from sqlalchemy import select

from app.models.alumni import AlumniEmployment, AlumniProfile
from app.models.user import UserRole
from tests.conftest import auth_header, make_user

pytestmark = pytest.mark.asyncio


async def add_profile(db, user, *, batch=2018, email_visible=False, phone_visible=False, phone=None):
    profile = AlumniProfile(
        user_id=user.id, batch_year=batch, department="EEE", graduation_date=date(batch + 4, 6, 1),
        membership_status="active", verified_by_admin=True, is_verified=True, is_visible=True,
        current_city="Sylhet", current_country="Bangladesh", email_visible=email_visible,
        phone_visible=phone_visible, phone=phone,
    )
    db.add(profile)
    await db.flush()
    return profile


async def test_batches_are_generated_without_hardcoded_rows(client):
    response = await client.get("/api/v1/alumni/batches")
    assert response.status_code == 200
    rows = response.json()
    assert rows[0] == {"year": 2010, "alumni_count": 0}
    assert rows[-1]["year"] == date.today().year
    assert len(rows) == date.today().year - 2009


async def test_standalone_directory_filters_and_redacts_contacts(client, db):
    viewer = await make_user(db, role=UserRole.STUDENT)
    first = await make_user(db, role=UserRole.ALUMNI, email="first@example.com")
    second = await make_user(db, role=UserRole.ALUMNI, email="second@example.com")
    first.full_name = "First Engineer"
    second.full_name = "Second Engineer"
    first_profile = await add_profile(db, first, batch=2018)
    second_profile = await add_profile(db, second, batch=2019, email_visible=True, phone_visible=True, phone="01700000000")
    db.add_all([
        AlumniEmployment(alumni_id=first_profile.id, organization="Power Grid Company", position="Engineer", sector="industry", country="Bangladesh", is_current=True),
        AlumniEmployment(alumni_id=second_profile.id, organization="Global University", position="Researcher", sector="academia", country="Germany", is_current=True),
    ])
    await db.commit()

    response = await client.get("/api/v1/alumni/", params={"batch": 2019, "company": "Global"}, headers=auth_header(viewer))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["full_name"] == "Second Engineer"
    assert body["items"][0]["email"] == "second@example.com"
    assert body["items"][0]["phone"] == "01700000000"

    response = await client.get("/api/v1/alumni/", params={"q": "Power Grid"}, headers=auth_header(viewer))
    assert response.status_code == 200
    assert response.json()["items"][0]["email"] is None
    assert response.json()["items"][0]["phone"] is None


async def test_alumni_can_edit_only_own_profile_and_employments(client, db):
    owner = await make_user(db, role=UserRole.ALUMNI)
    other = await make_user(db, role=UserRole.ALUMNI)
    owner_profile = await add_profile(db, owner)
    await add_profile(db, other, batch=2017)
    await db.commit()

    response = await client.patch("/api/v1/alumni/me", json={"bio": "Updated by owner", "phone": "01800000000"}, headers=auth_header(owner))
    assert response.status_code == 200
    assert response.json()["bio"] == "Updated by owner"
    assert response.json()["phone"] == "01800000000"

    response = await client.put("/api/v1/alumni/me/employments", json=[{
        "organization": "EEE Startup", "position": "Founder", "sector": "startup", "is_current": True,
    }], headers=auth_header(owner))
    assert response.status_code == 200, response.text
    assert response.json()[0]["organization"] == "EEE Startup"
    rows = list((await db.scalars(select(AlumniEmployment).where(AlumniEmployment.alumni_id == owner_profile.id))).all())
    assert len(rows) == 1


async def test_only_admin_can_import_and_preview_validates_csv(client, db):
    student = await make_user(db, role=UserRole.STUDENT)
    admin = await make_user(db, role=UserRole.SUPER_ADMIN)
    csv = b"email,full_name,batch_year,department,graduation_date,organization,sector\nnew@example.com,New Alumni,2009,EEE,2014-06-01,Example,industry\n"
    forbidden = await client.post("/api/v1/alumni/admin/import/preview", files={"file": ("alumni.csv", csv, "text/csv")}, headers=auth_header(student))
    assert forbidden.status_code == 403
    preview = await client.post("/api/v1/alumni/admin/import/preview", files={"file": ("alumni.csv", csv, "text/csv")}, headers=auth_header(admin))
    assert preview.status_code == 200
    assert preview.json()["valid_rows"] == 0
    assert preview.json()["invalid_rows"] == 1
    assert "2010" in preview.json()["errors"][0]["message"]


async def test_non_admin_cannot_verify_or_import(client, db):
    alumni = await make_user(db, role=UserRole.ALUMNI)
    await add_profile(db, alumni, batch=2016)
    await db.commit()
    response = await client.patch(f"/api/v1/alumni/admin/{alumni.id}/verify", headers=auth_header(alumni))
    assert response.status_code == 403
