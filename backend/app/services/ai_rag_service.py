from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.integrations.gemini_client import generate_gemini_response

class AIRagService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def answer_academic_query(self, query: str, course_code: str):
        if not settings.GEMINI_API_KEY:
            return {
                "answer": "AI assistant is not configured. Set GEMINI_API_KEY in your environment.",
                "citations": [],
            }
        prompt = f"Grounded context in SUST EEE course {course_code}. Student asks: {query}"
        ans = generate_gemini_response(prompt)
        return {"answer": ans, "citations": [f"{course_code} Lecture Handouts"]}
