from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.repositories.course_repository import CourseRepository
from app.schemas.academic import CourseOfferingResponse


class CourseService:
    """Course offerings, scoped to what the caller may see.

    Before this, `GET /courses` returned two hardcoded dicts for every caller
    -- a student saw courses they were not enrolled in, a teacher saw courses
    they did not teach, and the numbers were fiction. The endpoints now read
    the real tables through role-shaped queries.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CourseRepository(db)

    async def list_for_user(self, user: User) -> list[CourseOfferingResponse]:
        if user.role in (UserRole.STUDENT, UserRole.CR):
            rows = await self.repo.for_student(user.id)
        elif user.role == UserRole.TEACHER:
            rows = await self.repo.for_teacher(user.id)
        else:
            # Admin / lab assistant: oversight roles see the catalogue.
            rows = await self.repo.all_offerings()

        return [
            CourseOfferingResponse(
                id=offering_id,
                course_code=course_code,
                title=title,
                credit_hours=float(credit_hours),
                type=course_type,
                semester_title=semester_title,
                enrolled_students=int(enrolled_students or 0),
            )
            for offering_id, course_code, title, credit_hours, course_type, semester_title, enrolled_students in rows
        ]
