"""Contracts for course offerings, assignment requests and enrollment."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


PublicationStatus = Literal["draft", "published"]
AssignmentRequestStatus = Literal["pending", "approved", "rejected"]
EnrollmentStatus = Literal["enrolled", "main", "improvement", "drop"]
SemesterTargetTerm = Literal["1-1", "1-2", "2-1", "2-2", "3-1", "3-2", "4-1", "4-2"]


class CourseOfferingCreate(BaseModel):
    """Only catalogue and semester references are accepted from the client.

    Owner, publication state and credits are assigned/read on the server.
    """

    course_id: uuid.UUID
    semester_id: int = Field(gt=0)


class TeacherCourseOfferingCreate(BaseModel):
    """Catalogue data supplied by a teacher for a scoped semester offering."""

    model_config = ConfigDict(extra="forbid")

    course_code: str = Field(min_length=1, max_length=12)
    title: str = Field(min_length=1, max_length=150)
    credit_hours: Decimal = Field(
        gt=Decimal("0"),
        le=Decimal("99.9"),
        max_digits=3,
        decimal_places=1,
    )
    course_type: Literal["theory", "lab"]
    semester_id: int = Field(gt=0)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("course_code", mode="before")
    @classmethod
    def normalize_course_code(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("Course code must be a string.")
        value = value.strip().upper()
        if not value:
            raise ValueError("Course code must not be blank.")
        if len(value) > 12:
            raise ValueError("Course code must be at most 12 characters.")
        return value

    @field_validator("title", mode="before")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("Title must be a string.")
        value = value.strip()
        if not value:
            raise ValueError("Title must not be blank.")
        if len(value) > 150:
            raise ValueError("Title must be at most 150 characters.")
        return value

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Description must be a string.")
        value = value.strip()
        if len(value) > 500:
            raise ValueError("Description must be at most 500 characters.")
        return value or None


class CourseOfferingUpdate(BaseModel):
    course_id: uuid.UUID | None = None
    semester_id: int | None = Field(default=None, gt=0)


class CourseOfferingPublicationRequest(BaseModel):
    published: bool


class SemesterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    target_term: SemesterTargetTerm | None = None
    is_active: bool
    start_date: date
    end_date: date


class AssignedCourseTeacherResponse(BaseModel):
    teacher_id: uuid.UUID
    teacher_name: str
    role: str


class CourseOfferingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_id: uuid.UUID
    semester_id: int
    course_code: str
    course_title: str
    credit_hours: float
    course_type: str
    semester_title: str
    target_term: SemesterTargetTerm | None = None
    semester_is_active: bool
    publication_status: PublicationStatus
    assigned_teachers: list[AssignedCourseTeacherResponse] = Field(default_factory=list)
    created_by: uuid.UUID | None = None
    published_by: uuid.UUID | None = None
    published_at: datetime | None = None
    request_status: AssignmentRequestStatus | None = None


class TeacherAssignmentRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_offering_id: uuid.UUID
    teacher_id: uuid.UUID
    teacher_name: str
    course_code: str
    course_title: str
    semester_id: int
    semester_title: str
    status: AssignmentRequestStatus
    decided_by: uuid.UUID | None = None
    decided_at: datetime | None = None
    rejection_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class AssignmentDecisionRequest(BaseModel):
    decision: Literal["approve", "reject"]
    rejection_reason: str | None = Field(default=None, max_length=1000)


class EnrollmentCreate(BaseModel):
    enrollment_type: Literal["enrolled", "main", "improvement"] = "enrolled"


class EnrollmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_offering_id: uuid.UUID
    student_id: uuid.UUID
    status: EnrollmentStatus
    course_code: str
    course_title: str
    semester_id: int
    semester_title: str
    credit_hours: float
    enrolled_at: datetime
    updated_at: datetime
    dropped_at: datetime | None = None


class RosterEntryResponse(BaseModel):
    student_id: uuid.UUID
    identifier: str
    full_name: str
    email: str
    status: Literal["enrolled", "main", "improvement"]
    credit_hours: float


class ActiveCreditTotalResponse(BaseModel):
    active_credit_total: float

class CourseResponse(BaseModel):
    id: uuid.UUID
    course_code: str
    title: str
    credit_hours: float
    type: str

class ClassScheduleResponse(BaseModel):
    id: uuid.UUID
    course_code: str
    course_title: str
    day_of_week: str
    start_time: str
    end_time: str
    room_number: str
    instructor_name: str
    is_lab: bool
