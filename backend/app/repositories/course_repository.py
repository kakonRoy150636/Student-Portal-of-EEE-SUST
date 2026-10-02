from sqlalchemy import Row, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic import (
    Course,
    CourseEnrollment,
    CourseOffering,
    CourseOfferingTeacher,
    Semester,
)


class CourseRepository:
    """Offerings scoped by role.

    Three different questions, three queries: a student asks "what am I
    enrolled in", a teacher asks "what am I teaching", an admin asks "what
    exists". Encoding that here keeps the service free of role branching and
    makes each statement individually indexable.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    def _select(self):
        return (
            select(
                CourseOffering.id,
                Course.course_code,
                Course.title,
                Course.credit_hours,
                Course.type,
                Semester.title.label("semester_title"),
                func.count(CourseEnrollment.id).label("enrolled_students"),
            )
            .join(Course, Course.id == CourseOffering.course_id)
            .join(Semester, Semester.id == CourseOffering.semester_id, isouter=True)
            .join(CourseEnrollment, CourseEnrollment.course_offering_id == CourseOffering.id, isouter=True)
        )

    async def for_student(self, user_id) -> list[Row]:
        stmt = (
            self._select()
            .where(
                CourseOffering.id.in_(
                    select(CourseEnrollment.course_offering_id).where(
                        CourseEnrollment.student_id == user_id
                    )
                )
            )
            .group_by(
                CourseOffering.id, Course.course_code, Course.title,
                Course.credit_hours, Course.type, Semester.title,
            )
            .order_by(Course.course_code)
        )
        return list((await self.db.execute(stmt)).all())

    async def for_teacher(self, user_id) -> list[Row]:
        stmt = (
            self._select()
            .join(
                CourseOfferingTeacher,
                CourseOfferingTeacher.course_offering_id == CourseOffering.id,
            )
            .where(CourseOfferingTeacher.teacher_id == user_id)
            .group_by(
                CourseOffering.id, Course.course_code, Course.title,
                Course.credit_hours, Course.type, Semester.title,
            )
            .order_by(Course.course_code)
        )
        return list((await self.db.execute(stmt)).all())

    async def all_offerings(self) -> list[Row]:
        stmt = (
            self._select()
            .group_by(
                CourseOffering.id, Course.course_code, Course.title,
                Course.credit_hours, Course.type, Semester.title,
            )
            .order_by(Course.course_code)
        )
        return list((await self.db.execute(stmt)).all())
