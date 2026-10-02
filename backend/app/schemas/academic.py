import uuid
from datetime import time
from pydantic import BaseModel

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


class CourseOfferingResponse(BaseModel):
    """An offering as the caller is allowed to see it.

    `enrolled_students` is a count, not a roster: a student needs to know how
    full a section is, not who else is in it.
    """

    id: uuid.UUID
    course_code: str
    title: str
    credit_hours: float
    type: str
    semester_title: str | None = None
    enrolled_students: int = 0
