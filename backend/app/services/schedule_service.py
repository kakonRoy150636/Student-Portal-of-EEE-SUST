"""Weekly class routine.

The previous implementation returned a single hardcoded row ("Sample routine
aligned with SUST EEE 3-1 syllabus") for every caller, including teachers and
admins, and never touched `class_schedules` -- the table, its repository and
its Alembic revision all existed but nothing read them.

The routine is now built from `class_schedules` joined to the offering, the
course, the room and the instructor, filtered by how the caller relates to the
offering:

* student / CR  -> offerings they are enrolled in
* teacher       -> offerings they are assigned to teach
* admin / ER    -> everything (oversight)

Times are formatted for display here (`09:00 AM`) because the frontend's
`ScheduleCalendar` renders the string directly and the API contract predates
this change; the underlying column is a real ``TIME``.
"""

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic import (
    ClassSchedule,
    Course,
    CourseEnrollment,
    CourseOffering,
    CourseOfferingTeacher,
)
from app.models.facility import Room
from app.models.user import User, UserRole

# Sunday-first, matching the Bangladeshi academic week. Used to sort the
# routine so Friday/Saturday land at the end instead of alphabetically.
_DAY_ORDER = case(
    {"Sunday": 0, "Monday": 1, "Tuesday": 2, "Wednesday": 3, "Thursday": 4, "Friday": 5, "Saturday": 6},
    value=ClassSchedule.day_of_week,
    else_=7,
)


def _format_time(value) -> str:
    return value.strftime("%I:%M %p").lstrip("0") if value is not None else ""


class ScheduleService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_my_routine(self, user: User) -> list[dict]:
        stmt = (
            select(
                ClassSchedule.id,
                Course.course_code,
                Course.title,
                ClassSchedule.day_of_week,
                ClassSchedule.start_time,
                ClassSchedule.end_time,
                Room.room_number,
                Room.is_lab,
                User.full_name.label("instructor_name"),
            )
            .join(CourseOffering, CourseOffering.id == ClassSchedule.course_offering_id)
            .join(Course, Course.id == CourseOffering.course_id)
            .join(Room, Room.id == ClassSchedule.room_id, isouter=True)
            .join(User, User.id == ClassSchedule.instructor_id, isouter=True)
        )

        if user.role in (UserRole.STUDENT, UserRole.CR):
            stmt = stmt.where(
                ClassSchedule.course_offering_id.in_(
                    select(CourseEnrollment.course_offering_id).where(
                        CourseEnrollment.student_id == user.id,
                        # A dropped course must not keep appearing in the
                        # routine; the enrolment row stays for history.
                        CourseEnrollment.status != "drop",
                    )
                )
            )
        elif user.role == UserRole.TEACHER:
            stmt = stmt.where(
                ClassSchedule.course_offering_id.in_(
                    select(CourseOfferingTeacher.course_offering_id).where(
                        CourseOfferingTeacher.teacher_id == user.id
                    )
                )
            )
        # Admin / lab assistant: no filter -- oversight roles see the timetable.

        stmt = stmt.order_by(_DAY_ORDER, ClassSchedule.start_time)
        rows = (await self.db.execute(stmt)).all()

        return [
            {
                "id": str(schedule_id),
                "course_code": course_code,
                "course_title": title,
                "day_of_week": day_of_week,
                "start_time": _format_time(start_time),
                "end_time": _format_time(end_time),
                "room_number": room_number or "Unassigned",
                "instructor_name": instructor_name or "Not assigned",
                "is_lab": bool(is_lab),
            }
            for schedule_id, course_code, title, day_of_week, start_time, end_time, room_number, is_lab, instructor_name in rows
        ]

    async def get_today_classes(self, user: User) -> list[dict]:
        """The caller's classes for today, reusing the same scoping."""
        from datetime import date

        today = date.today().strftime("%A")
        return [row for row in await self.get_my_routine(user) if row["day_of_week"] == today]
