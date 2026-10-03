import uuid
from unittest.mock import AsyncMock

import pytest

from app.models.user import UserRole
from app.services.lab_service import LabService
from tests.conftest import make_user, auth_header

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize('role', list(UserRole))
async def test_equipment_staff_allowlist(client, db, monkeypatch, role):
    user = await make_user(db, role=role)
    query = AsyncMock(return_value=[])
    monkeypatch.setattr(LabService, 'list_equipment', query)
    response = await client.get('/api/v1/labs/equipment', headers=auth_header(user))
    staff = role in {UserRole.SUPER_ADMIN, UserRole.TEACHER, UserRole.LAB_ASSISTANT}
    assert response.status_code == (200 if staff else 403)
    assert query.await_count == int(staff)


@pytest.mark.parametrize('role', [r for r in UserRole if r != UserRole.SUPER_ADMIN])
async def test_all_admin_routes_reject_non_admins(client, db, role):
    user = await make_user(db, role=role)
    target = uuid.uuid4()
    routes = [
        ('GET', '/auth/admin/pending-approvals'),
        ('PATCH', f'/auth/admin/approve/{target}'),
        ('GET', '/alumni/admin/pending'),
        ('PATCH', f'/alumni/admin/approve/{target}'),
        ('PATCH', f'/alumni/admin/reject/{target}'),
        ('POST', '/alumni/events'),
        ('POST', '/alumni/scholarships'),
        ('PATCH', f'/alumni/scholarships/applications/{target}'),
    ]
    for method, path in routes:
        result = await client.request(method, '/api/v1'+path, json={}, headers=auth_header(user))
        assert result.status_code == 403, (role, path, result.text)


async def test_forged_role_claim_does_not_grant_staff_access(client, student):
    from app.core.security import create_access_token
    token = create_access_token({'sub': str(student.id), 'role': 'super_admin'})
    result = await client.get('/api/v1/labs/equipment', headers={'Authorization': 'Bearer '+token})
    assert result.status_code == 403
