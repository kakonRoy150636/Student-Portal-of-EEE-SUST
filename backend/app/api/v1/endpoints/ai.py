from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import TooManyRequestsException
from app.core.rate_limit import check_rate_limit
from app.models.user import User
from app.schemas.ai import AIAnswerResponse, AIHistoryMessage, AIQueryRequest
from app.api.pagination import page
from app.services.ai_rag_service import AIRagService

router = APIRouter(prefix="/ai", tags=["AI Copilot"])


@router.post("/query", response_model=AIAnswerResponse)
async def query_ai(
    payload: AIQueryRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Answer a course question from indexed department material.

    Retrieval always runs. A language model is used only when one is
    configured; otherwise the answer is assembled from the retrieved passages
    and labelled as such. Every query is capped per account because each one
    may spend a paid API call.
    """
    if not await check_rate_limit(
        f"ai-query:{user.id}",
        limit=settings.AI_MAX_QUERIES_PER_HOUR,
        window_seconds=3600,
    ):
        raise TooManyRequestsException(
            "You have reached the hourly limit for the assistant. Please try again later."
        )
    return await AIRagService(db).answer_academic_query(user, payload.prompt, payload.course_code)


@router.get("/history", response_model=list[AIHistoryMessage])
async def ai_history(
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """The caller's most recent assistant exchange, oldest first."""
    return page(await AIRagService(db).history(user), limit)
