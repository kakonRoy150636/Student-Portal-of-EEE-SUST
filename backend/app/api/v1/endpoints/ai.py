from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.ai_rag_service import AIRagService
from app.schemas.ai import AIQueryRequest, AIQueryResponse
from app.api.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/ai", tags=["AI Copilot"])

@router.post("/query", response_model=AIQueryResponse)
async def query_ai(payload: AIQueryRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    service = AIRagService(db)
    res = await service.answer_academic_query(payload.prompt, payload.course_code)
    return res
