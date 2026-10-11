"""Course workspace announcements and per-user read state."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AnnouncementType(str, enum.Enum):
    GENERAL = "general"
    CLASS_UPDATE = "class_update"
    CLASS_CANCELLED = "class_cancelled"
    EXAM = "exam"
    ASSIGNMENT = "assignment"
    URGENT = "urgent"
    RESOURCE = "resource"
    ADMINISTRATIVE = "administrative"


class AnnouncementStatus(str, enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class AnnouncementAudience(str, enum.Enum):
    ENROLLED_STUDENTS = "enrolled_students"
    CR_ONLY = "cr_only"
    TEACHERS_ONLY = "teachers_only"


ANNOUNCEMENT_TYPES = tuple(item.value for item in AnnouncementType)
ANNOUNCEMENT_STATUSES = tuple(item.value for item in AnnouncementStatus)
ANNOUNCEMENT_AUDIENCES = tuple(item.value for item in AnnouncementAudience)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CourseAnnouncement(Base, UUIDPrimaryKeyMixin):
    """A plain-text announcement scoped to one course offering."""

    __tablename__ = "course_announcements"
    __table_args__ = (
        CheckConstraint(
            "announcement_type IN ('general', 'class_update', 'class_cancelled', 'exam', "
            "'assignment', 'urgent', 'resource', 'administrative')",
            name="ck_course_announcements_type",
        ),
        CheckConstraint(
            "status IN ('draft', 'scheduled', 'published', 'archived')",
            name="ck_course_announcements_status",
        ),
        CheckConstraint(
            "audience IN ('enrolled_students', 'cr_only', 'teachers_only')",
            name="ck_course_announcements_audience",
        ),
        CheckConstraint(
            "(status != 'draft' OR publish_at IS NULL) AND "
            "(status NOT IN ('scheduled', 'published') OR publish_at IS NOT NULL) AND "
            "((status = 'archived' AND archived_at IS NOT NULL AND is_pinned = false) OR "
            "(status != 'archived' AND archived_at IS NULL))",
            name="ck_course_announcements_lifecycle",
        ),
        Index("ix_course_announcements_due", "status", "publish_at"),
        Index(
            "ix_course_announcements_offering_feed",
            "offering_id",
            "status",
            "publish_at",
            "is_pinned",
        ),
        Index(
            "ix_course_announcements_offering_created",
            "offering_id",
            "created_at",
        ),
    )

    offering_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("course_offerings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    # Body is stored as text only. The API strips markup before creating or
    # updating this row; this column is never an HTML template or URL store.
    body: Mapped[str] = mapped_column(Text, nullable=False)
    announcement_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default=AnnouncementType.GENERAL.value, server_default="general",
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=AnnouncementStatus.DRAFT.value, server_default="draft",
    )
    audience: Mapped[str] = mapped_column(
        String(30), nullable=False, default=AnnouncementAudience.ENROLLED_STUDENTS.value, server_default="enrolled_students",
    )
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow, server_default=func.now(),
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AnnouncementRead(Base):
    """The latest read time for one user and one announcement."""

    __tablename__ = "announcement_reads"
    __table_args__ = (
        PrimaryKeyConstraint("announcement_id", "user_id", name="pk_announcement_reads"),
        UniqueConstraint(
            "announcement_id",
            "user_id",
            name="uq_announcement_reads_announcement_user",
        ),
        Index(
            "ix_announcement_reads_announcement_user_read",
            "announcement_id",
            "user_id",
            "read_at",
        ),
        Index("ix_announcement_reads_user_read", "user_id", "read_at"),
    )

    announcement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("course_announcements.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    read_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now(),
    )


# A descriptive alias for callers that name the state after its parent
# resource. It intentionally points at the same mapped class/table.
CourseAnnouncementRead = AnnouncementRead


class CourseResource(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Offering-specific publication state for an existing academic resource."""

    __tablename__ = "course_resources"
    __table_args__ = (
        UniqueConstraint("offering_id", "resource_id", name="uq_course_resources_offering_resource"),
        Index("ix_course_resources_offering_state", "offering_id", "is_published", "archived_at"),
    )

    offering_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("course_offerings.id", ondelete="CASCADE"), nullable=False,
    )
    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academic_resources.id", ondelete="CASCADE"), nullable=False,
    )
    published_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CourseEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Published course event/deadline metadata."""

    __tablename__ = "course_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('class', 'quiz', 'midterm', 'final', 'viva', 'assignment_deadline', "
            "'lab_exam', 'presentation', 'holiday', 'other')",
            name="ck_course_events_type",
        ),
        CheckConstraint(
            "reminder_minutes IS NULL OR reminder_minutes BETWEEN 0 AND 10080",
            name="ck_course_events_reminder",
        ),
        Index("ix_course_events_offering_start", "offering_id", "starts_at", "archived_at"),
    )

    offering_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("course_offerings.id", ondelete="CASCADE"), nullable=False,
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False, default="other", server_default="other")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    reminder_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CourseQuestion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Moderated student question and teacher answer in one course."""

    __tablename__ = "course_questions"
    __table_args__ = (
        CheckConstraint("status IN ('open', 'answered', 'resolved', 'closed')", name="ck_course_questions_status"),
        CheckConstraint("visibility IN ('course', 'private')", name="ck_course_questions_visibility"),
        Index("ix_course_questions_offering_state", "offering_id", "status", "created_at"),
    )

    offering_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("course_offerings.id", ondelete="CASCADE"), nullable=False,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open", server_default="open")
    visibility: Mapped[str] = mapped_column(String(20), nullable=False, default="course", server_default="course")
    answer_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    answered_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


__all__ = [
    "AnnouncementAudience",
    "AnnouncementStatus",
    "AnnouncementType",
    "AnnouncementRead",
    "CourseAnnouncementRead",
    "CourseAnnouncement",
    "CourseResource",
    "CourseEvent",
    "CourseQuestion",
]
