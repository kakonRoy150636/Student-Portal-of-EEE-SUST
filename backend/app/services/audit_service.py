"""Append-only record of who changed what.

Before this service, approvals, booking decisions, file deletions and password
resets left no trace at all: an administrator could deactivate an account or
decide a request and the portal kept no record of it. This module writes one
row per security-relevant action.

Design notes
------------
* Every call writes through the caller's session, so an audit row commits (or
  rolls back) with the change it describes. A booking decision that fails to
  commit does not produce an audit entry claiming it happened.
* ``detail`` is JSON text and deliberately never receives a password, token or
  secret. Callers pass short, structural context (old/new value, reason).
* The actor is nullable so a rejected login against an unknown identifier can
  still be recorded.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import structlog
from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog

logger = structlog.get_logger(__name__)

MAX_DETAIL_CHARS = 2000


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record(
        self,
        *,
        action: str,
        entity_type: str,
        entity_id: str | uuid.UUID | None = None,
        actor_id: uuid.UUID | None = None,
        detail: dict[str, Any] | None = None,
        request: Request | None = None,
        commit: bool = False,
    ) -> None:
        """Write one audit row.

        ``commit=True`` is for paths that have nothing else to commit (a failed
        login attempt, a rejected request). Everything else lets the caller's
        own commit persist the row atomically with the change.
        """
        entry = AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            detail=self._serialise(detail),
            ip_address=_client_ip(request),
            user_agent=_truncate(request.headers.get("user-agent") if request else None, 255),
        )
        self.db.add(entry)
        if commit:
            try:
                await self.db.commit()
            except Exception:  # pragma: no cover - defensive
                # An audit write must never turn a handled request into a 500.
                logger.exception("audit_write_failed", action=action)
                await self.db.rollback()
        else:
            await self.db.flush()

    async def list_entries(
        self, *, limit: int = 50, offset: int = 0, action: str | None = None
    ) -> list[AuditLog]:
        stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        return list((await self.db.execute(stmt)).scalars().all())

    async def count(self, *, action: str | None = None) -> int:
        stmt = select(func.count()).select_from(AuditLog)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        return int((await self.db.execute(stmt)).scalar() or 0)

    @staticmethod
    def _serialise(detail: dict[str, Any] | None) -> str | None:
        if not detail:
            return None
        try:
            text = json.dumps(detail, default=str, sort_keys=True)
        except (TypeError, ValueError):  # pragma: no cover - defensive
            text = str(detail)
        return text[:MAX_DETAIL_CHARS]


def _client_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    # Local import to avoid a circular dependency (dependencies imports models).
    from app.api.dependencies import get_client_ip

    return get_client_ip(request)


def _truncate(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    return value[:limit]
