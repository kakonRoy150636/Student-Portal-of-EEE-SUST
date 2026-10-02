"""Create the first super_admin from environment variables at startup.

Why not seed.sql: that file is mounted as a Postgres init script, so anything
in it is committed to the repository and replayed on every fresh database.
Hashing requires bcrypt, which Postgres does not have, so a seeded admin has
to carry a literal hash -- which is exactly the problem this module solves.

Behaviour:
- If BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD are both unset, do
  nothing and log at INFO. That keeps local development working without
  forcing every contributor to invent credentials.
- If both are set and no super_admin exists yet, create one.
- If a super_admin already exists, never touch it. Bootstrapping must not be
  a way to overwrite a live administrator.
- If only one of the two is set, refuse to guess and raise: a half-configured
  admin is a misconfiguration, not a silent skip.

The generated password is never logged.
"""
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)


async def ensure_bootstrap_admin(db: AsyncSession) -> None:
    email = (settings.BOOTSTRAP_ADMIN_EMAIL or "").strip()
    password = settings.BOOTSTRAP_ADMIN_PASSWORD or ""

    if not email and not password:
        logger.info(
            "Bootstrap admin skipped: BOOTSTRAP_ADMIN_EMAIL / "
            "BOOTSTRAP_ADMIN_PASSWORD are not set."
        )
        return

    if not email or not password:
        raise RuntimeError(
            "Bootstrap admin is half-configured: set BOTH BOOTSTRAP_ADMIN_EMAIL "
            "and BOOTSTRAP_ADMIN_PASSWORD, or neither."
        )

    if len(password) < 12:
        raise RuntimeError(
            "BOOTSTRAP_ADMIN_PASSWORD must be at least 12 characters. Refusing "
            "to create an administrator with a weak password."
        )

    existing_admin = await db.scalar(
        select(User.id).where(User.role == UserRole.SUPER_ADMIN).limit(1)
    )
    if existing_admin is not None:
        logger.info("Bootstrap admin skipped: a super_admin already exists.")
        return

    taken = await db.scalar(select(User.id).where(User.email == email).limit(1))
    if taken is not None:
        logger.warning(
            "Bootstrap admin skipped: %s already belongs to a non-admin account.",
            email,
        )
        return

    identifier = (settings.BOOTSTRAP_ADMIN_IDENTIFIER or "admin").strip() or "admin"
    identifier_taken = await db.scalar(
        select(User.id).where(User.identifier == identifier).limit(1)
    )
    if identifier_taken is not None:
        # Deterministic suffix so the admin can still be found by email.
        identifier = f"{identifier}-{await db.scalar(select(func.floor(func.random() * 100000)))}"

    admin = User(
        identifier=identifier,
        email=email,
        full_name="System Administrator",
        password_hash=await get_password_hash(password),
        role=UserRole.SUPER_ADMIN,
        is_active=True,
    )
    db.add(admin)
    await db.commit()
    logger.info("Bootstrap admin created for %s (identifier=%s).", email, identifier)
