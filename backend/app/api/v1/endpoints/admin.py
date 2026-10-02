"""Administrative read surfaces: the audit trail."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import RequireRole
from app.core.database import get_db
from app.models.user import User, UserRole
from app.services.audit_service import AuditService

router = APIRouter(prefix="/admin", tags=["Administration"])


class AuditLogEntry(BaseModel):
    id: Any
    actor_id: Any | None = None
    action: str
    entity_type: str
    entity_id: str | None = None
    detail: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class AuditLogPage(BaseModel):
    total: int
    items: list[AuditLogEntry]


@router.get("/audit-logs", response_model=AuditLogPage)
async def list_audit_logs(
    action: str | None = Query(default=None, max_length=64),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0, le=100_000),
    _: User = Depends(RequireRole([UserRole.SUPER_ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """Newest first, optionally filtered by action verb."""
    service = AuditService(db)
    return AuditLogPage(
        total=await service.count(action=action),
        items=[AuditLogEntry.model_validate(row) for row in await service.list_entries(
            limit=limit, offset=offset, action=action
        )],
    )
