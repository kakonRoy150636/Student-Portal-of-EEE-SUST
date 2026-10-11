"""Strict API contracts for the course workspace."""

from __future__ import annotations

import html
import re
import uuid
from datetime import date, datetime
from html.parser import HTMLParser
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

AnnouncementTypeValue = Literal[
    "general",
    "class_update",
    "class_cancelled",
    "exam",
    "assignment",
    "urgent",
    "resource",
    "administrative",
]
AnnouncementStatusValue = Literal["draft", "scheduled", "published", "archived"]
EditableAnnouncementStatus = Literal["draft", "scheduled", "published"]
AnnouncementAudienceValue = Literal["enrolled_students", "cr_only", "teachers_only"]
EventTypeValue = Literal[
    "class", "quiz", "midterm", "final", "viva", "assignment_deadline",
    "lab_exam", "presentation", "holiday", "other",
]
QuestionStatusValue = Literal["open", "answered", "resolved", "closed"]
QuestionVisibilityValue = Literal["course", "private"]

MAX_ANNOUNCEMENT_TITLE = 200
MAX_ANNOUNCEMENT_BODY = 20_000


class _PlainTextParser(HTMLParser):
    """Convert markup to readable text while discarding executable elements."""

    _SKIP_TAGS = {"script", "style", "template", "iframe", "object", "embed"}
    _BLOCK_TAGS = {"br", "div", "li", "p", "pre", "section", "tr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1
        elif self._skip_depth == 0 and tag in self._BLOCK_TAGS:
            self.parts.append("\n")

    def handle_startendtag(self, tag: str, attrs) -> None:
        if self._skip_depth == 0 and tag.lower() in self._BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
        elif self._skip_depth == 0 and tag.lower() in self._BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self.parts.append(data)


def sanitize_plain_text(value: str) -> str:
    """Return bounded, readable text with all markup removed.

    Announcement bodies are intentionally not rendered as HTML.  Parsing with
    ``HTMLParser`` also handles entities without preserving an attacker-owned
    tag or script body in the database.
    """

    if not isinstance(value, str):
        raise ValueError("Announcement text must be a string.")
    # Decode before parsing, including nested entities. Decoding after parsing
    # could turn &lt;script&gt; back into executable markup in stored text.
    for _ in range(5):
        decoded = html.unescape(value)
        if decoded == value:
            break
        value = decoded
    parser = _PlainTextParser()
    parser.feed(value)
    parser.close()
    text = "".join(parser.parts)
    # Malformed/incomplete markup is data to HTMLParser. Keep it readable but
    # never persist HTML delimiters, even for a consumer that renders wrongly.
    text = text.replace("<", "‹").replace(">", "›")
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    # Keep line breaks useful while preventing control characters from being
    # persisted as invisible content.
    text = re.sub(r"[\t\f\v ]+", " ", text)
    text = re.sub(r"\n[ ]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _clean_announcement_text(value: str, *, field_name: str, maximum: int) -> str:
    if not isinstance(value, str) or len(value) > maximum:
        raise ValueError(f"{field_name} must be a string of at most {maximum} characters.")
    cleaned = sanitize_plain_text(value)
    if not cleaned:
        raise ValueError(f"{field_name} must not be blank.")
    if len(cleaned) > maximum:
        raise ValueError(f"{field_name} must be at most {maximum} characters.")
    return cleaned


class CourseAnnouncementCreate(BaseModel):
    # ``extra=forbid`` is the important strictness boundary here. Pydantic's
    # normal JSON parsing is retained for ISO-8601 publish_at strings.
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=MAX_ANNOUNCEMENT_TITLE)
    body: str = Field(min_length=1, max_length=MAX_ANNOUNCEMENT_BODY)
    announcement_type: AnnouncementTypeValue = "general"
    audience: AnnouncementAudienceValue = "enrolled_students"
    status: Literal["draft", "scheduled", "published"] = "draft"
    publish_at: datetime | None = None

    @field_validator("title", mode="before")
    @classmethod
    def clean_title(cls, value: str) -> str:
        return _clean_announcement_text(value, field_name="Title", maximum=MAX_ANNOUNCEMENT_TITLE)

    @field_validator("body", mode="before")
    @classmethod
    def clean_body(cls, value: str) -> str:
        return _clean_announcement_text(value, field_name="Body", maximum=MAX_ANNOUNCEMENT_BODY)

    @field_validator("publish_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("publish_at must include a timezone.")
        return value

    @model_validator(mode="after")
    def validate_schedule(self) -> "CourseAnnouncementCreate":
        if self.status == "scheduled" and self.publish_at is None:
            raise ValueError("Scheduled announcements require publish_at.")
        if self.status == "draft" and self.publish_at is not None:
            raise ValueError("Draft announcements cannot have publish_at.")
        return self


class CourseAnnouncementUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=MAX_ANNOUNCEMENT_TITLE)
    body: str | None = Field(default=None, min_length=1, max_length=MAX_ANNOUNCEMENT_BODY)
    announcement_type: AnnouncementTypeValue | None = None
    audience: AnnouncementAudienceValue | None = None
    status: EditableAnnouncementStatus | None = None
    publish_at: datetime | None = None

    @field_validator("title", mode="before")
    @classmethod
    def clean_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _clean_announcement_text(value, field_name="Title", maximum=MAX_ANNOUNCEMENT_TITLE)

    @field_validator("body", mode="before")
    @classmethod
    def clean_body(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _clean_announcement_text(value, field_name="Body", maximum=MAX_ANNOUNCEMENT_BODY)

    @field_validator("publish_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        return CourseAnnouncementCreate.require_timezone(value)

    @model_validator(mode="after")
    def reject_null_fields(self) -> "CourseAnnouncementUpdate":
        for field_name in self.model_fields_set - {"publish_at"}:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null.")
        return self


class AnnouncementPinRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, populate_by_name=True)

    pinned: bool = Field(alias="is_pinned")


class AnnouncementPermissions(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    can_manage: bool
    can_publish: bool
    can_edit: bool
    can_archive: bool
    can_pin: bool


class CourseAnnouncementResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: uuid.UUID
    offering_id: uuid.UUID
    author_id: uuid.UUID
    author_name: str
    title: str
    body: str
    announcement_type: AnnouncementTypeValue
    status: AnnouncementStatusValue
    audience: AnnouncementAudienceValue
    is_pinned: bool
    publish_at: datetime | None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None
    is_read: bool
    can_manage: bool
    can_publish: bool
    can_edit: bool
    can_archive: bool
    can_pin: bool


class CourseAnnouncementFeedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    items: list[CourseAnnouncementResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
    has_more: bool


class WorkspaceCourseResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: uuid.UUID
    course_code: str
    title: str
    credit_hours: float
    type: str
    description: str | None


class WorkspaceSemesterResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: int
    title: str
    target_term: str | None
    is_active: bool
    start_date: date
    end_date: date


class WorkspaceTeacherResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    teacher_id: uuid.UUID
    teacher_name: str
    role: str


class WorkspaceScheduleResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: uuid.UUID
    day_of_week: str
    start_time: str
    end_time: str
    room_number: str | None
    instructor_name: str | None
    is_lab: bool | None


class CourseAnnouncementReadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    announcement_id: uuid.UUID
    read_at: datetime
    is_read: bool = True


class CourseResourceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: uuid.UUID
    title: str
    description: str | None = None
    category: str
    course_id: uuid.UUID
    file_name: str
    file_size_bytes: int
    mime_type: str
    download_count: int
    is_faculty_verified: bool
    created_at: datetime
    is_published: bool
    archived_at: datetime | None = None
    can_manage: bool = False


class CourseResourceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_published: bool | None = None
    archived: bool | None = None

    @model_validator(mode="after")
    def require_change(self) -> "CourseResourceUpdate":
        if self.is_published is None and self.archived is None:
            raise ValueError("Provide is_published or archived.")
        return self


class CourseEventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    event_type: EventTypeValue = "other"
    starts_at: datetime
    ends_at: datetime | None = None
    location: str | None = Field(default=None, max_length=200)
    reminder_minutes: int | None = Field(default=None, ge=0, le=10080)
    is_published: bool = True

    @field_validator("title", "description", "location", mode="before")
    @classmethod
    def clean_text(cls, value):
        if value is None:
            return None
        cleaned = sanitize_plain_text(value)
        return cleaned or None

    @field_validator("starts_at", "ends_at")
    @classmethod
    def require_timezone(cls, value: datetime | None):
        if value is not None and value.tzinfo is None:
            raise ValueError("Event times must include a timezone.")
        return value

    @model_validator(mode="after")
    def validate_times(self) -> "CourseEventCreate":
        if self.ends_at is not None and self.starts_at is not None and self.ends_at < self.starts_at:
            raise ValueError("Event end must not be before its start.")
        return self


class CourseEventUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    event_type: EventTypeValue | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    location: str | None = Field(default=None, max_length=200)
    reminder_minutes: int | None = Field(default=None, ge=0, le=10080)
    is_published: bool | None = None

    @field_validator("title", "description", "location", mode="before")
    @classmethod
    def clean_update_text(cls, value):
        if value is None:
            return None
        cleaned = sanitize_plain_text(value)
        return cleaned or None

    @field_validator("starts_at", "ends_at")
    @classmethod
    def require_update_timezone(cls, value: datetime | None):
        if value is not None and value.tzinfo is None:
            raise ValueError("Event times must include a timezone.")
        return value

    @model_validator(mode="after")
    def validate_update_times(self) -> "CourseEventUpdate":
        if self.starts_at is not None and self.ends_at is not None and self.ends_at < self.starts_at:
            raise ValueError("Event end must not be before its start.")
        return self


class CourseEventResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: uuid.UUID
    offering_id: uuid.UUID
    author_id: uuid.UUID
    author_name: str
    title: str
    description: str | None
    event_type: EventTypeValue
    starts_at: datetime
    ends_at: datetime | None
    location: str | None
    reminder_minutes: int | None
    is_published: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    can_manage: bool = False


class CourseQuestionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=10000)
    visibility: QuestionVisibilityValue = "course"

    @field_validator("title", "body", mode="before")
    @classmethod
    def clean_text(cls, value):
        if not isinstance(value, str):
            raise ValueError("Question text must be a string.")
        cleaned = sanitize_plain_text(value)
        if not cleaned:
            raise ValueError("Question text must not be blank.")
        return cleaned


class CourseQuestionAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer_body: str = Field(min_length=1, max_length=10000)
    status: Literal["answered", "resolved", "closed"] = "answered"

    @field_validator("answer_body", mode="before")
    @classmethod
    def clean_answer(cls, value: str) -> str:
        cleaned = sanitize_plain_text(value)
        if not cleaned:
            raise ValueError("Answer must not be blank.")
        return cleaned


class CourseQuestionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: uuid.UUID
    offering_id: uuid.UUID
    student_id: uuid.UUID
    student_name: str
    title: str
    body: str
    status: QuestionStatusValue
    visibility: QuestionVisibilityValue
    answer_body: str | None
    answered_by: uuid.UUID | None
    answered_at: datetime | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime
    can_manage: bool = False
    can_answer: bool = False
    can_edit: bool = False


class CourseWorkspaceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    offering_id: uuid.UUID
    offering_status: Literal["draft", "published"]
    course: WorkspaceCourseResponse
    semester: WorkspaceSemesterResponse
    authorized_teachers: list[WorkspaceTeacherResponse]
    active_enrollment_count: int = Field(ge=0)
    unread_announcement_count: int = Field(ge=0)
    recent_activity: list[CourseAnnouncementResponse]
    upcoming_schedules: list[WorkspaceScheduleResponse]
    resources: list[CourseResourceResponse]
    events: list[CourseEventResponse]
    questions: list[CourseQuestionResponse]
    permissions: AnnouncementPermissions
    can_manage: bool
    can_publish: bool
    can_edit: bool
    can_archive: bool
    can_pin: bool
    links: dict[str, str]


__all__ = [
    "AnnouncementAudienceValue",
    "AnnouncementPinRequest",
    "AnnouncementPermissions",
    "AnnouncementStatusValue",
    "AnnouncementTypeValue",
    "CourseEventCreate",
    "CourseEventResponse",
    "CourseEventUpdate",
    "CourseAnnouncementCreate",
    "CourseAnnouncementFeedResponse",
    "CourseAnnouncementReadResponse",
    "CourseAnnouncementResponse",
    "CourseAnnouncementUpdate",
    "CourseQuestionAnswer",
    "CourseQuestionCreate",
    "CourseQuestionResponse",
    "CourseResourceResponse",
    "CourseResourceUpdate",
    "CourseWorkspaceResponse",
    "MAX_ANNOUNCEMENT_BODY",
    "MAX_ANNOUNCEMENT_TITLE",
    "sanitize_plain_text",
]
