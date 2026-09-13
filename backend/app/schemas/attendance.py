class AttendanceRecordUpdate(BaseModel):
    student_id: uuid.UUID
    status: str

class AttendanceUpdateSchema(BaseModel):
    records: list[AttendanceRecordUpdate]

class StudentAttendanceSummary(BaseModel):
    student_id: uuid.UUID
    full_name: str
    total_sessions: int
    present_count: int
    percentage: float
    below_threshold: bool