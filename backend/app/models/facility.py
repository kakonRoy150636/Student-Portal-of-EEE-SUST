import uuid
from sqlalchemy import String, Boolean, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
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
    __tablename__ = "room_reservations"

    room_id: Mapped[int] = mapped_column(Integer, ForeignKey("rooms.id"), nullable=False)
    reserved_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    purpose: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    approved_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
