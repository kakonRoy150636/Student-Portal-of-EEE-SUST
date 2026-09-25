"""Response models for the post-login dashboard summary.

Kept permissive on purpose: the payload is role-scoped, so a caller only ever
receives the section relevant to them, and optional fields exist so a tile can
be omitted (None) rather than forcing a fake zero.
"""
from typing import Optional

from pydantic import BaseModel, Field


class RoutineEntry(BaseModel):
    course_code: str
    course_title: str
    day_of_week: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    room_number: Optional[str] = None
    building: Optional[str] = None


class StudentSummary(BaseModel):
    enrolled_courses: int = 0
    total_classes: int = 0
    attended: int = 0
    attendance_percentage: Optional[float] = None
    below_attendance_threshold: Optional[bool] = None
    credit_hours: float = 0.0
    today_classes: int = 0
    routine: list[RoutineEntry] = Field(default_factory=list)
    unread_notifications: int = 0
    opportunities: int = 0


class TeacherSummary(BaseModel):
    assigned_courses: int = 0
    students_taught: int = 0
    today_classes: int = 0
    pending_equipment_requests: int = 0
    pending_room_requests: int = 0
    pending_project_proposals: int = 0
    unread_notifications: int = 0


class ErSummary(BaseModel):
    equipment_total: int = 0
    equipment_under_repair: int = 0
    pending_borrow_requests: int = 0
    rooms_total: int = 0
    pending_room_requests: int = 0
    unread_notifications: int = 0


class AlumniSummary(BaseModel):
    visible_alumni: int = 0
    active_alumni: int = 0
    mentorship_pairs: int = 0
    career_opportunities: int = 0
    unread_notifications: int = 0


class AdminSummary(BaseModel):
    users_total: int = 0
    users_active: int = 0
    pending_approvals: int = 0
    users_by_role: dict[str, int] = Field(default_factory=dict)
    pending_alumni_claims: int = 0
    active_alumni: int = 0
    pending_room_requests: int = 0
    rooms_total: int = 0
    equipment_total: int = 0
    pending_equipment_requests: int = 0
    courses: int = 0
    projects: int = 0
    unread_notifications: int = 0


class DashboardSummaryResponse(BaseModel):
    """Only the section matching the caller's role is populated."""

    role: str
    student: Optional[StudentSummary] = None
    teacher: Optional[TeacherSummary] = None
    er: Optional[ErSummary] = None
    alumni: Optional[AlumniSummary] = None
    admin: Optional[AdminSummary] = None
