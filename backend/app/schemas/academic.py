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
