"""Post-login dashboard summary.

Thin, like every other module here: authenticate, delegate to
DashboardService, return the response model. No ORM access and no business
rules in this file.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardSummaryResponse
from app.services.dashboard_service import build_summary

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
async def dashboard_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Live, role-scoped counters for the logged-in user's homepage.

    Replaces the frozen strings the dashboards used to render, so every tile
    is a real aggregate evaluated at request time.
    """
    return await build_summary(db, user)
