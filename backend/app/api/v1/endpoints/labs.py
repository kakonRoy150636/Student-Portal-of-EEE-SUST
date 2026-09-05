from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.lab_service import LabService
from app.api.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/labs", tags=["Lab Management"])

@router.get("/equipment")
async def get_equipment(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    service = LabService(db)
    return await service.list_equipment()
