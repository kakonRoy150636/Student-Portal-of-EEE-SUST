import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AIQueryRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=1000)
    course_code: str | None = Field(default=None, max_length=12)


class AICitation(BaseModel):
    document_title: str
    course_code: str | None = None
    snippet: str


class AIAnswerResponse(BaseModel):
    answer: str
    citations: list[AICitation] = []
    # True only when a language model wrote the answer from retrieved context.
    # The UI shows a different badge otherwise, so a student is never told a
    # quoted passage is a synthesised answer.
    grounded: bool = False
    mode: str = "no-context"
    session_id: uuid.UUID | None = None


class AIHistoryMessage(BaseModel):
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class StudyPlanRequest(BaseModel):
    topics: list[str] = Field(..., min_length=1, max_length=20)
    days: int = Field(..., ge=1, le=60)


class StudyPlanResponse(BaseModel):
    plan: str
    mode: str
