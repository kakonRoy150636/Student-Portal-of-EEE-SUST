from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic import (
    ClassSchedule,
    Course,
    CourseEnrollment,
    CourseOffering,
)
from app.models.facility import Room
from app.models.user import User


class ScheduleService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_my_routine(self, user_id):
        """Return the caller's own class routine from the database.

        Previously this returned a hardcoded single-entry sample, which made
        every student see the same invented EEE 311 slot. The routine is
        derived from the student's own course enrolments, so two students in
        different offerings get different timetables.
        """
        stmt = (
            select(
                ClassSchedule,
                Course.course_code,
                Course.title,
                Room.room_number,
                Room.is_lab,
                User.full_name.label("instructor_name"),
            )
            .join(CourseOffering, ClassSchedule.course_offering_id == CourseOffering.id)
            .join(Course, CourseOffering.course_id == Course.id)
            .join(Room, ClassSchedule.room_id == Room.id)
            .join(
                CourseEnrollment,
                CourseEnrollment.course_offering_id == CourseOffering.id,
            )
            .join(User, ClassSchedule.instructor_id == User.id, isouter=True)
            .where(CourseEnrollment.student_id == user_id)
            .order_by(ClassSchedule.day_of_week, ClassSchedule.start_time)
        )
        rows = (await self.db.execute(stmt)).all()

        routine = []
        for entry, course_code, course_title, room_number, is_lab, instructor_name in rows:
            routine.append(
                {
                    "id": str(entry.id),
                    "course_code": course_code,
                    "course_title": course_title,
                    "day_of_week": entry.day_of_week,
                    "start_time": entry.start_time.strftime("%I:%M %p") if entry.start_time else None,
                    "end_time": entry.end_time.strftime("%I:%M %p") if entry.end_time else None,
                    "room_number": room_number,
                    "instructor_name": instructor_name,
                    "is_lab": bool(is_lab),
                }
            )
        return routine
