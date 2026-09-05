from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.project_service import ProjectService
from app.api.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/projects", tags=["Project Hub"])

@router.get("")
async def get_projects(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    service = ProjectService(db)
    return await service.list_capstones()
