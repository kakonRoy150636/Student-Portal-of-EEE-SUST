"""Create the first administrator from the environment, once.

`database/seed.sql` used to ship a super_admin whose bcrypt hash was committed
to the repository, which made the administrative password offline-checkable by
anyone who could read the source. Accounts are no longer seeded at all.

Instead, an operator supplies BOOTSTRAP_ADMIN_EMAIL / BOOTSTRAP_ADMIN_PASSWORD
(or their identifier/name variants) and the first application start creates
that account -- with ``must_change_password=True``, so the environment value is
a one-time credential rather than a permanent password. From then on the
account is managed through the portal like any other.

If the variables are unset and no super_admin exists, startup logs
``bootstrap_admin_missing`` and continues: the portal stays up so people can
register, and the operator can set the variables and restart.
"""

from __future__ import annotations

import structlog
from sqlalchemy import func, select

from app.core.config import settings
from app.core.passwords import hash_password
from app.core.security import MAX_PASSWORD_BYTES
from app.models.user import User, UserRole

logger = structlog.get_logger(__name__)

# The bootstrap credential is a one-time, forced-change password; it still must
# not be trivially short, because there is a window between creation and the
# first sign-in.
MIN_BOOTSTRAP_PASSWORD_LENGTH = 12


async def ensure_bootstrap_admin(session_factory) -> None:
    """Idempotently create the environment-provided administrator."""
    if not settings.BOOTSTRAP_ADMIN_EMAIL and not settings.BOOTSTRAP_ADMIN_PASSWORD:
        await _warn_if_no_administrator(session_factory)
        return

    if not settings.BOOTSTRAP_ADMIN_EMAIL or not settings.BOOTSTRAP_ADMIN_PASSWORD:
        logger.error(
            "bootstrap_admin_incomplete",
            hint="set both BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD",
        )
        return

    password_bytes = settings.BOOTSTRAP_ADMIN_PASSWORD.encode("utf-8")
    if len(password_bytes) < MIN_BOOTSTRAP_PASSWORD_LENGTH or len(password_bytes) > MAX_PASSWORD_BYTES:
        logger.error(
            "bootstrap_admin_password_rejected",
            hint=(
                "BOOTSTRAP_ADMIN_PASSWORD must be between "
                f"{MIN_BOOTSTRAP_PASSWORD_LENGTH} and {MAX_PASSWORD_BYTES} bytes"
            ),
        )
        return

    try:
        async with session_factory() as db:
            existing = (
                await db.execute(
                    select(func.count()).select_from(User).where(User.role == UserRole.SUPER_ADMIN)
                )
            ).scalar() or 0

            if existing:
                logger.debug("bootstrap_admin_skipped", reason="an administrator already exists")
                return

            admin = User(
                identifier=settings.BOOTSTRAP_ADMIN_IDENTIFIER or "admin",
                email=settings.BOOTSTRAP_ADMIN_EMAIL,
                full_name=settings.BOOTSTRAP_ADMIN_NAME or "System Administrator",
                password_hash=await hash_password(settings.BOOTSTRAP_ADMIN_PASSWORD),
                role=UserRole.SUPER_ADMIN,
                is_active=True,
                # The environment password is a handover credential; the holder
                # cannot use the rest of the API until they replace it.
                must_change_password=True,
            )
            db.add(admin)
            try:
                await db.commit()
            except Exception:
                # Two workers racing at start-up both see zero administrators;
                # the unique index lets exactly one win. Losing the race is the
                # expected outcome, not an error.
                await db.rollback()
                logger.debug("bootstrap_admin_skipped", reason="created concurrently")
                return

            # Never log the identifier/password beyond what is already in the
            # configuration; the email is enough to confirm what happened.
            logger.warning(
                "bootstrap_admin_created",
                email=settings.BOOTSTRAP_ADMIN_EMAIL,
                must_change_password=True,
            )
    except Exception:
        # A database that is not ready yet must not stop the API from starting;
        # every request would fail anyway and the next restart retries.
        logger.exception("bootstrap_admin_failed")


async def _warn_if_no_administrator(session_factory) -> None:
    try:
        async with session_factory() as db:
            existing = (
                await db.execute(
                    select(func.count()).select_from(User).where(User.role == UserRole.SUPER_ADMIN)
                )
            ).scalar() or 0
    except Exception:
        return
    if not existing:
        logger.warning(
            "bootstrap_admin_missing",
            hint=(
                "no super_admin exists; set BOOTSTRAP_ADMIN_EMAIL and "
                "BOOTSTRAP_ADMIN_PASSWORD and restart to create one"
            ),
        )
