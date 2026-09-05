from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.schedule_service import ScheduleService
from app.api.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/schedules", tags=["Schedules"])

@router.get("/my-routine")
async def get_routine(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = ScheduleService(db)
    return await service.get_my_routine(user.id)
