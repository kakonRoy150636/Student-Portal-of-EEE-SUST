"""Contracts for course offerings, assignment requests and enrollment."""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


PublicationStatus = Literal["draft", "published"]
AssignmentRequestStatus = Literal["pending", "approved", "rejected"]
EnrollmentStatus = Literal["enrolled", "main", "improvement", "drop"]


class CourseOfferingCreate(BaseModel):
    """Only catalogue and semester references are accepted from the client.

    Owner, publication state and credits are assigned/read on the server.
    """

    course_id: uuid.UUID
    semester_id: int = Field(gt=0)


class CourseOfferingUpdate(BaseModel):
    course_id: uuid.UUID | None = None
    semester_id: int | None = Field(default=None, gt=0)


class CourseOfferingPublicationRequest(BaseModel):
    published: bool


class SemesterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
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
