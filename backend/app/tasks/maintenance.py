"""Housekeeping tasks that stop tables growing without bound."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import delete, or_

from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.models.auth import PasswordResetToken, RefreshToken

logger = structlog.get_logger(__name__)

# Refresh rows are kept for a short grace window after they die so an operator
# investigating a theft report can still see the rotation history.
REFRESH_RETENTION_DAYS = 7
RESET_RETENTION_DAYS = 30


async def cleanup(db) -> dict:
    """Prune dead tokens using the caller's session (so it is testable)."""
    now = datetime.now(timezone.utc)
    refresh_cutoff = now - timedelta(days=REFRESH_RETENTION_DAYS)
    reset_cutoff = now - timedelta(days=RESET_RETENTION_DAYS)

    # Expired or revoked refresh tokens. Without this the table -- which
    # gains a row on every login and every rotation -- only ever grows.
    refresh_result = await db.execute(
        delete(RefreshToken).where(
            or_(
                RefreshToken.expires_at < refresh_cutoff,
                (RefreshToken.is_revoked.is_(True))
                & (RefreshToken.expires_at < now),
            )
        )
    )
    # Password reset tokens are single-use and short-lived; used and
    # expired ones have no value after the grace window.
    reset_result = await db.execute(
        delete(PasswordResetToken).where(
            or_(
                PasswordResetToken.expires_at < reset_cutoff,
                (PasswordResetToken.is_used.is_(True))
                & (PasswordResetToken.expires_at < reset_cutoff),
            )
        )
    )
    await db.commit()

    summary = {
        "refresh_tokens_deleted": refresh_result.rowcount or 0,
        "password_reset_tokens_deleted": reset_result.rowcount or 0,
    }
    logger.info("token_cleanup_complete", **summary)
    return summary


async def _cleanup() -> dict:
    async with AsyncSessionLocal() as db:
        return await cleanup(db)


@celery_app.task(name="app.tasks.maintenance.cleanup_expired_tokens")
def cleanup_expired_tokens() -> dict:
    return asyncio.run(_cleanup())
