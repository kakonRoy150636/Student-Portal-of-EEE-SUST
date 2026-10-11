import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator


AttendanceStatus = Literal["present", "absent", "late", "excused"]


def _reject_duplicate_students(model):
    student_ids = [record.student_id for record in model.records]
    if len(student_ids) != len(set(student_ids)):
        raise ValueError("Each student may appear only once per attendance request.")
    return model


class AttendanceRecordCreate(BaseModel):
    student_id: uuid.UUID
    status: AttendanceStatus = "present"


class AttendanceSessionCreate(BaseModel):
    course_offering_id: uuid.UUID
    session_date: date
    topic_discussed: str | None = Field(default=None, max_length=255)
    records: list[AttendanceRecordCreate] = Field(default_factory=list, max_length=500)

    _unique_students = model_validator(mode="after")(_reject_duplicate_students)


class AttendanceRecordUpdate(BaseModel):
    student_id: uuid.UUID
    status: AttendanceStatus


class AttendanceUpdateSchema(BaseModel):
    records: list[AttendanceRecordUpdate] = Field(max_length=500)

    _unique_students = model_validator(mode="after")(_reject_duplicate_students)


class StudentAttendanceSummary(BaseModel):
    student_id: uuid.UUID
    full_name: str
    total_sessions: int
    present_count: int
    percentage: float
    below_threshold: bool
