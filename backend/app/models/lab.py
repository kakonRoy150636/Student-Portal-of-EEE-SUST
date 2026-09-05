import uuid
from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

class EquipmentModel(Base):
    __tablename__ = "equipment_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_name: Mapped[str] = mapped_column(String(150), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    total_quantity: Mapped[int] = mapped_column(Integer, default=1)
    available_quantity: Mapped[int] = mapped_column(Integer, default=1)

class EquipmentAsset(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "equipment_assets"

    model_id: Mapped[int] = mapped_column(Integer, ForeignKey("equipment_models.id"), nullable=False)
    asset_tag: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    lab_name: Mapped[str] = mapped_column(String(100), nullable=False)
    condition: Mapped[str] = mapped_column(String(30), default="operational")

class EquipmentBorrowRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "equipment_borrow_requests"

    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("equipment_assets.id"), nullable=False)
    borrower_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    supervising_teacher_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    purpose: Mapped[str] = mapped_column(String(255), nullable=False)
    borrow_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expected_return: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending_approval")

class DamageReport(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "damage_reports"

    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("equipment_assets.id"), nullable=False)
    reported_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    resolved: Mapped[bool] = mapped_column(Integer, default=False)
