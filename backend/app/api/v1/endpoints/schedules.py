from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import RequireRole, get_current_user
from app.core.database import get_db
from app.models.user import User, UserRole
from app.schemas.academic import ClassScheduleResponse
from app.api.pagination import page
from app.services.schedule_service import ScheduleService

router = APIRouter(prefix="/schedules", tags=["Schedules"])

ROUTINE_ROLES = [UserRole.STUDENT, UserRole.CR, UserRole.TEACHER, UserRole.SUPER_ADMIN]


@router.get("/my-routine", response_model=list[ClassScheduleResponse])
async def get_routine(
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0, le=100_000),
    user: User = Depends(RequireRole(ROUTINE_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """The caller's own weekly timetable, built from `class_schedules`."""
    return page(await ScheduleService(db).get_my_routine(user), limit, offset)
