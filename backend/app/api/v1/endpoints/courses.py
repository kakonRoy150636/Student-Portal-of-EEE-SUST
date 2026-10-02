"""Course catalogue endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.academic import Course
from app.models.user import User

router = APIRouter(prefix="/courses", tags=["Courses"])


@router.get("")
async def list_courses(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return the course catalogue.

    Replaces a hardcoded pair of EEE 311/312 dicts that every caller received
    regardless of what the department had actually created. Catalogue rows are
    reference data maintained by admins, so they are read straight from the
    courses table.
    """
    rows = (
        await db.execute(select(Course).order_by(Course.course_code))
    ).scalars().all()

    return [
        {
            "id": str(course.id),
            "course_code": course.course_code,
            "title": course.title,
            "credits": float(course.credit_hours),
            "type": course.type,
            "description": course.description,
        }
        for course in rows
    ]
