import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

class UserDevice(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "user_devices"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    fcm_token: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    platform: Mapped[str] = mapped_column(String(20), default="web")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    enable_push: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_10m_class_alert: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_lab_reminders: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_exam_alerts: Mapped[bool] = mapped_column(Boolean, default=True)

class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"
    __table_args__ = (
        # One class alert per (class_session, recipient): keeps the Celery Beat
        # 1-minute scanner idempotent even if two scans overlap.
        UniqueConstraint("recipient_id", "class_session_id", name="uq_notification_class_session", deferrable=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recipient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(String(500), nullable=False)
    data_payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    # Optional reference to the class schedule row this alert is about; used for idempotency.
    class_session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("class_schedules.id"), nullable=True)
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)