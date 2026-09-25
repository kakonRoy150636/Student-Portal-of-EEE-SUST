import uuid
from datetime import date
from sqlalchemy import String, Boolean, Date, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

ALUMNI_POSTED_TAG = "alumni-posted"

class CareerOpportunity(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "career_opportunities"

    posted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    organization_name: Mapped[str] = mapped_column(String(150), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    location: Mapped[str] = mapped_column(String(120), nullable=True)
    application_deadline: Mapped[date] = mapped_column(Date, nullable=False)
    application_target: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    tags: Mapped[list] = mapped_column(ARRAY(String), default=list)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=True)

class StudentCVProfile(Base):
    __tablename__ = "student_cv_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    headline: Mapped[str] = mapped_column(String(200), nullable=True)
    summary: Mapped[str] = mapped_column(String(500), nullable=True)
    education: Mapped[dict] = mapped_column(JSONB, default=list)
    skills: Mapped[dict] = mapped_column(JSONB, default=dict)
    experience: Mapped[dict] = mapped_column(JSONB, default=list)

class StudentPortfolio(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "student_portfolios"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    slug: Mapped[str] = mapped_column(String(60), unique=True, index=True, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    view_count: Mapped[int] = mapped_column(default=0)
