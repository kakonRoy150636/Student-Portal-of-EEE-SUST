import re

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.ai_budget import reserve_ai
from app.integrations.gemini_client import GeminiClient, GeminiUnavailable, maximum_query_cost, embedding_cost, generation_cost
from app.services.ai_retrieval import AcademicRetriever, NOT_FOUND, clean_text


class AIRagService:
    def __init__(self, db: AsyncSession, *, provider=None):
        self.db = db
        self.provider = provider or GeminiClient()

    async def answer_academic_query(self, query: str, course_code: str, user_id):
        retriever = AcademicRetriever(self.db)
        available = await retriever.has_sources(course_code)
        if available and not settings.GEMINI_API_KEY:
            raise HTTPException(503, "AI assistant is not configured")
        reservation = await reserve_ai(user_id, maximum_query_cost(query) if available else 0)
        fallback = {'answer': NOT_FOUND, 'citations': [], 'grounded': False,
                    'quota_remaining': reservation.remaining}
        if not available:
            await reservation.settle(0)
            return fallback
        cost = 0
        try:
            vector = None
            if settings.AI_RRF_VECTOR_WEIGHT and await retriever.has_vectors(course_code):
                vector = await self.provider.embed(query)
                cost += embedding_cost(query)
            chunks = await retriever.retrieve(query, course_code, vector)
            # Confidence uses lexical coverage/cosine evidence, NOT RRF rank score.
            sources = [chunk for chunk in chunks if chunk.confident]
            if not sources:
                await reservation.settle(cost)
                return fallback
            result = await self.provider.generate(query, course_code, sources)
            cost += generation_cost(result)
            await reservation.settle(cost)
        except GeminiUnavailable:
            # On uncertainty do NOT release/retry the reservation: it still
            # counts against the cap until this admission day's keys expire.
            raise HTTPException(503, "AI assistant is temporarily unavailable. Please try later.") from None
        data = result.data
        ids = data.get('source_ids')
        answer = data.get('answer')
        valid = {f'S{i}': chunk for i, chunk in enumerate(sources, 1)}
        if (data.get('abstain') is not False or not isinstance(answer, str) or not answer.strip() or
                not isinstance(ids, list) or not ids or any(not isinstance(ident, str) or ident not in valid for ident in ids)):
            return fallback
        markers = set(re.findall(r'\[(S\d+)\]', answer))
        if not markers or markers != set(ids):
            return fallback
        citations = [{
            'source_id': ident, 'chunk_id': valid[ident].id,
            'document_name': valid[ident].document_name,
            'page_number': valid[ident].page_number, 'section': valid[ident].section,
        } for ident in dict.fromkeys(ids)]
        return {'answer': clean_text(answer, 8000), 'citations': citations, 'grounded': True,
                'quota_remaining': reservation.remaining}
