import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import String, Boolean, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB, TSTZRANGE, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    room_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    building: Mapped[str] = mapped_column(String(100), default="Department of EEE, IICT Building")
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    is_lab: Mapped[bool] = mapped_column(Boolean, default=False)
    amenities: Mapped[dict] = mapped_column(JSONB, default=dict)


class RoomReservation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A room/lab booking request.

    The live database stores the booked interval in a ``TSTZRANGE`` column
    guarded by a GiST exclusion constraint so that overlapping **active**
    (pending/approved) reservations for the same room are rejected at the
    database layer — even under concurrent requests.

    Cancelled and rejected rows intentionally fall outside the exclusion
    predicate (``WHERE status IN ('pending','approved')``) so they never block
    a slot.
    """

    __tablename__ = "room_reservations"
    __table_args__ = (
        ExcludeConstraint(
            ("room_id", "="),
            ("slot_range", "&&"),
            using="gist",
            name="no_overlapping_room_bookings",
            where="status IN ('pending', 'approved')",
        ),
    )

    room_id: Mapped[int] = mapped_column(Integer, ForeignKey("rooms.id"), nullable=False)
    reserved_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    purpose: Mapped[str] = mapped_column(String(255), nullable=False)
    # NOTE: bound/read via tstzrange()/lower()/upper() SQL helpers so the app
    # stays driver-agnostic (asyncpg has no first-class tstzrange codec).
    slot_range: Mapped[Any] = mapped_column(TSTZRANGE, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cancelled_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cancellation_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)