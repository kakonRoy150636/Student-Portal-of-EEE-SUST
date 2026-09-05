import uuid
from datetime import date
from sqlalchemy import String, Date, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

class AttendanceSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "attendance_sessions"

    course_offering_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("course_offerings.id"), nullable=False)
    session_date: Mapped[date] = mapped_column(Date, default=date.today)
    taken_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    topic_discussed: Mapped[str] = mapped_column(String(255), nullable=True)

class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("attendance_sessions.id"), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="present")
