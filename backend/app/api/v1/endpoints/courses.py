from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.academic import CourseOfferingResponse
from app.api.pagination import page
from app.services.course_service import CourseService

router = APIRouter(prefix="/courses", tags=["Courses"])


@router.get("", response_model=list[CourseOfferingResponse])
async def list_courses(
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0, le=100_000),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Course offerings the caller is entitled to see.

    Students get their enrolments, teachers their assignments, admins the
    catalogue. This used to return two literal dicts to everyone.
    """
    return page(await CourseService(db).list_for_user(user), limit, offset)
