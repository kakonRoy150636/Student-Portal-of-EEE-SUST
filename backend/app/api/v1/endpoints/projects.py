from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.project import ProjectResponse
from app.api.pagination import page
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["Project Hub"])


@router.get("", response_model=list[ProjectResponse])
async def get_projects(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0, le=100_000),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Capstone and thesis projects, newest first, with supervisor and team size."""
    return page(await ProjectService(db).list_capstones(), limit, offset)
