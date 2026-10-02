import uuid
from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class AuditLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Append-only record of security-relevant actions.

    Approving an account, deciding a booking, deleting a file, resetting a
    password, enrolling or disabling a second factor: all of these change who
    can do what, and none of them left a trace before this table. The actor is
    nullable so a failed login attempt against an unknown identifier can still
    be recorded.
    """

    __tablename__ = "audit_logs"

    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    # Stable machine-readable verb, e.g. "reservation.decide", "user.approve".
    action: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[Optional[str]] = mapped_column(String(64))
    # Free-form context. Never put a password, token or secret in here.
    detail: Mapped[Optional[str]] = mapped_column(Text)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(String(255))
