from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.career import CareerOpportunityResponse
from app.api.pagination import page
from app.services.career_service import CareerService

router = APIRouter(prefix="/career", tags=["Career Portal"])


@router.get("/opportunities", response_model=list[CareerOpportunityResponse])
async def get_opportunities(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0, le=100_000),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Verified opportunities with an open deadline, most urgent first."""
    return page(await CareerService(db).list_active_circulars(), limit, offset)
