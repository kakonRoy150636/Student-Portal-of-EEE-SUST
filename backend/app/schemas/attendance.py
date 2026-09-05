import uuid
from datetime import date
from pydantic import BaseModel

class AttendanceRecordCreate(BaseModel):
    student_id: uuid.UUID
    status: str = "present"

class AttendanceSessionCreate(BaseModel):
    course_offering_id: uuid.UUID
    session_date: date
    topic_discussed: str | None = None
    records: list[AttendanceRecordCreate] = []
