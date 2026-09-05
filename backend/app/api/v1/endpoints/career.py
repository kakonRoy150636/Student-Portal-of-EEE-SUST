from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.career_service import CareerService
from app.api.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/career", tags=["Career Portal"])

@router.get("/opportunities")
async def get_opportunities(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    service = CareerService(db)
    return await service.list_active_circulars()
