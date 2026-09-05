import uuid
from sqlalchemy import String, Boolean, BigInteger, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

class AcademicResource(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "academic_resources"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)
    uploader_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    file_key: Mapped[str] = mapped_column(String(512), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    is_faculty_verified: Mapped[bool] = mapped_column(Boolean, default=False)

class BookExchange(Base):
    __tablename__ = "book_exchanges"

    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("academic_resources.id"), primary_key=True)
    author: Mapped[str] = mapped_column(String(200), nullable=False)
    edition: Mapped[str] = mapped_column(String(50), nullable=True)
    transaction_type: Mapped[str] = mapped_column(String(20), default="lend")
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
