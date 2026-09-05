from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.attendance_service import AttendanceService
from app.api.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/attendance", tags=["Attendance"])

@router.get("/my-summary")
async def get_my_summary(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = AttendanceService(db)
    return await service.get_student_summary(user.id)
