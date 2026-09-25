"""Pydantic contracts for the Alumni Portal."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator, model_validator


MembershipStatus = Literal["pending", "active", "expired", "rejected"]
EventType = Literal["reunion", "webinar", "meetup"]
RsvpStatus = Literal["attending", "interested", "not_attending"]
ScholarshipStatus = Literal["submitted", "under_review", "approved", "rejected"]
MentorshipStatus = Literal["requested", "active", "ended", "declined"]


class AlumniRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(..., min_length=6)
    batch_year: int = Field(..., ge=1960, le=2100)
    department: str = Field(..., min_length=2, max_length=100)
    graduation_date: date
    current_company: str | None = Field(None, max_length=150)
    designation: str | None = Field(None, max_length=150)
    industry: str | None = Field(None, max_length=100)
    linkedin_url: str | None = Field(None, max_length=255)

    @field_validator("linkedin_url")
    @classmethod
    def validate_linkedin(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        if not (value.startswith("http://") or value.startswith("https://")):
            raise ValueError("linkedin_url must start with http:// or https://")
        return value


class AlumniProfileCreate(BaseModel):
    """Existing portal users submit a batch/department claim."""

    batch_year: int = Field(..., ge=1960, le=2100)
    department: str = Field(..., min_length=2, max_length=100)
    graduation_date: date
    current_company: str | None = Field(None, max_length=150)
    designation: str | None = Field(None, max_length=150)
    industry: str | None = Field(None, max_length=100)
    linkedin_url: str | None = Field(None, max_length=255)
    is_visible: bool = False


class AlumniProfileUpdate(BaseModel):
    batch_year: int | None = Field(None, ge=1960, le=2100)
    department: str | None = Field(None, min_length=2, max_length=100)
    graduation_date: date | None = None
    current_company: str | None = Field(None, max_length=150)
    designation: str | None = Field(None, max_length=150)
    industry: str | None = Field(None, max_length=100)
    linkedin_url: str | None = Field(None, max_length=255)
    is_visible: bool | None = None


class AlumniUserSummary(BaseModel):
    id: uuid.UUID
    full_name: str
    identifier: str
    email: EmailStr | None = None
    avatar_key: str | None = None

    class Config:
        from_attributes = True


class AlumniProfileResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    batch_year: int
    department: str
    graduation_date: date
    current_company: str | None = None
    designation: str | None = None
    industry: str | None = None
    linkedin_url: str | None = None
    verified_by_admin: bool
    membership_status: str
    is_visible: bool
    created_at: datetime
    updated_at: datetime
    user: AlumniUserSummary | None = None

    class Config:
        from_attributes = True


class AlumniVerificationDecision(BaseModel):
    reason: str | None = Field(None, max_length=255)


class EventCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=3, max_length=2000)
    venue: str = Field(..., min_length=2, max_length=200)
    starts_at: datetime
    ends_at: datetime
    cover_photo_key: str | None = Field(None, max_length=512)
    is_published: bool = False
    members_only: bool = False
    event_type: EventType = "meetup"
    capacity: int | None = Field(None, ge=1)

    @model_validator(mode="after")
    def validate_window(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class EventUpdate(BaseModel):
    title: str | None = Field(None, min_length=3, max_length=200)
    description: str | None = Field(None, min_length=3, max_length=2000)
    venue: str | None = Field(None, min_length=2, max_length=200)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    cover_photo_key: str | None = Field(None, max_length=512)
    is_published: bool | None = None
    members_only: bool | None = None
    event_type: EventType | None = None
    capacity: int | None = Field(None, ge=1)

    @model_validator(mode="after")
    def validate_window(self):
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class EventResponse(BaseModel):
    id: uuid.UUID
    created_by: uuid.UUID
    title: str
    description: str
    venue: str
    starts_at: datetime
    ends_at: datetime
    cover_photo_key: str | None = None
    is_published: bool
    members_only: bool
    event_type: str
    capacity: int | None = None
    announced_at: datetime | None = None
    attending_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EventRsvpRequest(BaseModel):
    rsvp_status: RsvpStatus = "attending"
    note: str | None = Field(None, max_length=500)


class EventRsvpResponse(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    user_id: uuid.UUID
    rsvp_status: str
    note: str | None = None
    created_at: datetime
    updated_at: datetime
    event: EventResponse | None = None

    class Config:
        from_attributes = True


class ScholarshipCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=3, max_length=2000)
    eligibility: str = Field(..., min_length=3, max_length=1000)
    amount_bdt: int | None = Field(None, ge=0)
    deadline: date
    application_target: str = Field(..., min_length=2, max_length=255)
    is_published: bool = False


class ScholarshipUpdate(BaseModel):
    title: str | None = Field(None, min_length=3, max_length=200)
    description: str | None = Field(None, min_length=3, max_length=2000)
    eligibility: str | None = Field(None, min_length=3, max_length=1000)
    amount_bdt: int | None = Field(None, ge=0)
    deadline: date | None = None
    application_target: str | None = Field(None, min_length=2, max_length=255)
    is_published: bool | None = None


class ScholarshipResponse(BaseModel):
    id: uuid.UUID
    created_by: uuid.UUID
    title: str
    description: str
    eligibility: str
    amount_bdt: int | None = None
    deadline: date
    application_target: str
    is_published: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScholarshipApplyRequest(BaseModel):
    motivation: str = Field(..., min_length=10, max_length=2000)
    document_key: str | None = Field(None, max_length=512)
    document_name: str | None = Field(None, max_length=255)


class ScholarshipApplicationResponse(BaseModel):
    id: uuid.UUID
    scholarship_id: uuid.UUID
    applicant_id: uuid.UUID
    motivation: str
    document_key: str | None = None
    document_name: str | None = None
    status: str
    reviewed_by: uuid.UUID | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    scholarship: ScholarshipResponse | None = None

    class Config:
        from_attributes = True


class ScholarshipReviewRequest(BaseModel):
    status: ScholarshipStatus


class MentorshipRequest(BaseModel):
    mentor_id: uuid.UUID
    mentee_note: str | None = Field(None, max_length=1000)


class MentorshipRespondRequest(BaseModel):
    mentor_note: str | None = Field(None, max_length=1000)


class MentorshipPairResponse(BaseModel):
    id: uuid.UUID
    mentor_id: uuid.UUID
    mentee_id: uuid.UUID
    status: str
    requested_by: uuid.UUID
    mentee_note: str | None = None
    mentor_note: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    mentor: AlumniUserSummary | None = None
    mentee: AlumniUserSummary | None = None

    class Config:
        from_attributes = True


class NewsCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    body: str = Field(..., min_length=10, max_length=20000)
    cover_photo_key: str | None = Field(None, max_length=512)
    is_published: bool = False
    slug: str | None = Field(None, max_length=220)


class NewsUpdate(BaseModel):
    title: str | None = Field(None, min_length=3, max_length=200)
    body: str | None = Field(None, min_length=10, max_length=20000)
    cover_photo_key: str | None = Field(None, max_length=512)
    is_published: bool | None = None


class NewsPostResponse(BaseModel):
    id: uuid.UUID
    author_id: uuid.UUID
    title: str
    slug: str
    body: str
    cover_photo_key: str | None = None
    is_published: bool
    published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GalleryAlbumCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: str | None = Field(None, max_length=1000)
    event_id: uuid.UUID | None = None
    cover_photo_key: str | None = Field(None, max_length=512)
    is_published: bool = False


class GalleryAlbumUpdate(BaseModel):
    title: str | None = Field(None, min_length=2, max_length=200)
    description: str | None = Field(None, max_length=1000)
    event_id: uuid.UUID | None = None
    cover_photo_key: str | None = Field(None, max_length=512)
    is_published: bool | None = None


class GalleryPhotoCreate(BaseModel):
    photo_key: str = Field(..., min_length=3, max_length=512)
    caption: str | None = Field(None, max_length=500)
    sort_order: int = 0


class GalleryPhotoResponse(BaseModel):
    id: uuid.UUID
    album_id: uuid.UUID
    photo_key: str
    caption: str | None = None
    sort_order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GalleryAlbumResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None = None
    event_id: uuid.UUID | None = None
    cover_photo_key: str | None = None
    is_published: bool
    created_at: datetime
    updated_at: datetime
    photos: list[GalleryPhotoResponse] = []

    class Config:
        from_attributes = True


class PresignedUploadRequest(BaseModel):
    filename: str = Field(..., min_length=3, max_length=255)
    purpose: Literal["scholarship", "gallery", "event", "news"] = "scholarship"


class PresignedUploadResponse(BaseModel):
    file_key: str
    upload_url: str
    content_type: str


class AlumniLandingStats(BaseModel):
    active_alumni: int
    published_events: int
    open_scholarships: int
    published_news: int
    batches: int


class AlumniLandingResponse(BaseModel):
    stats: AlumniLandingStats
    news: list[NewsPostResponse]
    events: list[EventResponse]
    gallery: list[GalleryAlbumResponse]
    scholarships: list[ScholarshipResponse]


class AlumniDashboardResponse(BaseModel):
    profile: AlumniProfileResponse | None = None
    events: list[EventRsvpResponse]
    applications: list[ScholarshipApplicationResponse]
    mentorship: list[MentorshipPairResponse]
    pending_verification: bool = False
