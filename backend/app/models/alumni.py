"""Alumni Portal models.

Modeled on the Dhaka University Alumni Association (duaa-bd.org) layout:
a public-facing landing page (news, events, scholarships, gallery) plus an
authenticated members' area (directory, RSVPs, mentorship, applications).

All timestamps are stored timezone-aware (UTC); the API converts to
Asia/Dhaka only at display time, matching the rest of the portal.
"""
from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import INT4RANGE, ExcludeConstraint, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class MembershipStatus(str, enum.Enum):
    """Alumni membership lifecycle, verified by an admin."""

    PENDING = "pending"
    ACTIVE = "active"
    EXPIRED = "expired"
    REJECTED = "rejected"


class EventType(str, enum.Enum):
    REUNION = "reunion"
    WEBINAR = "webinar"
    MEETUP = "meetup"


class ScholarshipApplicationStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class AlumniProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "alumni_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_alumni_profiles_user"),
        Index("ix_alumni_profiles_batch_industry", "batch_year", "industry"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    batch_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    # Kept free-form on purpose (e.g. "EEE", "EEE (Power)"); the rest of the
    # schema uses VARCHAR for department-like fields.
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    graduation_date: Mapped[date] = mapped_column(Date, nullable=False)
    current_company: Mapped[str | None] = mapped_column(String(150))
    designation: Mapped[str | None] = mapped_column(String(150))
    industry: Mapped[str | None] = mapped_column(String(100), index=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(255))
    verified_by_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    membership_status: Mapped[str] = mapped_column(
        String(20), default=MembershipStatus.PENDING.value, nullable=False, index=True
    )
    # Opt-in: only visible profiles appear in the public directory / search.
    is_visible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    # search_tsv is a generated Postgres tsvector (see schema.sql / migration 005).
    # It is not mapped here so SQLite test metadata can still create the table.

    user: Mapped["User"] = relationship("User", back_populates="alumni_profile")


class Event(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "events"

    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False)
    venue: Mapped[str] = mapped_column(String(200), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cover_photo_key: Mapped[str | None] = mapped_column(String(512))
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    # Admins can flag an event as members-only; RSVP is then restricted.
    members_only: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    event_type: Mapped[str] = mapped_column(
        String(20), default=EventType.MEETUP.value, nullable=False, index=True
    )
    # NULL capacity == unlimited; otherwise RSVP "attending" rows are assigned
    # a seat in [1..capacity] and guarded against overbooking (see EventRSVP).
    capacity: Mapped[int | None] = mapped_column(Integer)
    # Set by the Celery Beat announcer the first time a published event's FCM
    # broadcast goes out; makes the minute-scanner idempotent.
    announced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    rsvps: Mapped[list["EventRSVP"]] = relationship(back_populates="event", cascade="all, delete-orphan")


class EventRSVP(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "event_rsvps"
    __table_args__ = (
        UniqueConstraint("event_id", "user_id", name="uq_event_rsvps_event_user"),
        # Same GiST-exclusion idea as room booking: each attending RSVP claims a
        # disjoint [seat, seat] point range for the event, so the database
        # rejects overbooking even under concurrent requests. Non-attending rows
        # carry a NULL slot and never consume capacity.
        ExcludeConstraint(
            ("event_id", "="),
            ("slot_range", "&&"),
            using="gist",
            name="no_double_booked_event_seats",
            where="rsvp_status = 'attending'",
        ),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # attending / interested / not_attending
    rsvp_status: Mapped[str] = mapped_column(String(20), default="attending", nullable=False)
    note: Mapped[str | None] = mapped_column(String(500))
    slot_range: Mapped[Any] = mapped_column(INT4RANGE, nullable=True)

    event: Mapped["Event"] = relationship(back_populates="rsvps")


class Scholarship(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "scholarships"

    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False)
    eligibility: Mapped[str] = mapped_column(String(1000), nullable=False)
    amount_bdt: Mapped[int | None] = mapped_column(Integer)
    deadline: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    application_target: Mapped[str] = mapped_column(String(255), nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    applications: Mapped[list["ScholarshipApplication"]] = relationship(
        back_populates="scholarship", cascade="all, delete-orphan"
    )


class ScholarshipApplication(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "scholarship_applications"
    __table_args__ = (
        UniqueConstraint("scholarship_id", "applicant_id", name="uq_scholarship_applications"),
    )

    scholarship_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scholarships.id", ondelete="CASCADE"), nullable=False
    )
    applicant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    motivation: Mapped[str] = mapped_column(String(2000), nullable=False)
    document_key: Mapped[str | None] = mapped_column(String(512))
    document_name: Mapped[str | None] = mapped_column(String(255))
    # submitted / under_review / approved / rejected
    status: Mapped[str] = mapped_column(
        String(20), default=ScholarshipApplicationStatus.SUBMITTED.value, nullable=False
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    scholarship: Mapped["Scholarship"] = relationship(back_populates="applications")


class MentorshipPair(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "mentorship_pairs"
    __table_args__ = (
        UniqueConstraint("mentor_id", "mentee_id", name="uq_mentorship_pairs"),
        Index("ix_mentorship_pairs_mentee", "mentee_id", "status"),
    )

    mentor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    mentee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # requested / active / ended / declined
    status: Mapped[str] = mapped_column(String(20), default="requested", nullable=False)
    requested_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    mentee_note: Mapped[str | None] = mapped_column(String(1000))
    mentor_note: Mapped[str | None] = mapped_column(String(1000))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class NewsPost(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "news_posts"

    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), unique=True, index=True, nullable=False)
    body: Mapped[str] = mapped_column(String(20000), nullable=False)
    cover_photo_key: Mapped[str | None] = mapped_column(String(512))
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GalleryAlbum(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "gallery_albums"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000))
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id", ondelete="SET NULL")
    )
    cover_photo_key: Mapped[str | None] = mapped_column(String(512))
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    photos: Mapped[list["GalleryPhoto"]] = relationship(back_populates="album", cascade="all, delete-orphan")


class GalleryPhoto(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "gallery_photos"

    album_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gallery_albums.id", ondelete="CASCADE"), nullable=False
    )
    photo_key: Mapped[str] = mapped_column(String(512), nullable=False)
    caption: Mapped[str | None] = mapped_column(String(500))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    album: Mapped["GalleryAlbum"] = relationship(back_populates="photos")