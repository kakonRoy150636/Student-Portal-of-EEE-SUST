"""Retrieval-augmented academic assistant.

What this replaces: ``AIRagService`` used to build a prompt string and return
``f"Grounded response for EEE students: {prompt}. (Armature reaction and
synchronous machine dynamics apply)."`` -- a canned sentence with no retrieval,
no model call and no citations, presented to students as an AI answer. The
``document_chunks``/``knowledge_documents`` tables, the pgvector column and
the ingestion task all existed but nothing read or wrote them.

Pipeline now:

1. Retrieve the top-k chunks relevant to the question. Vector search via the
   ``embedding`` column when an embedding model is configured and the database
   supports it; otherwise Postgres full-text search over ``tsv_content``, and
   ILIKE as the last resort (SQLite in tests).
2. If nothing in the knowledge base matches, say so explicitly. It does not
   invent an answer.
3. Otherwise ask Gemini to answer *only* from the retrieved passages, with the
   passages included in the prompt. If Gemini is not configured or fails, fall
   back to an extractive answer built from those passages and label it as such
   (``grounded=False`` + ``mode``), so a student can tell the difference.
4. Persist the exchange in ``ai_chat_sessions``/``ai_chat_messages`` so the
   assistant has memory and the history survives a reload.
"""

from __future__ import annotations

import json
import re
import uuid

from sqlalchemy import case, cast, func, literal_column, select
from sqlalchemy.exc import ProgrammingError, OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.integrations import gemini_client
from app.models.academic import Course
from app.models.ai_knowledge import AIChatMessage, AIChatSession, DocumentChunk, KnowledgeDocument
from app.models.types import Vector
from app.models.user import User
from app.schemas.ai import AIAnswerResponse, AICitation, AIHistoryMessage

_SYSTEM_INSTRUCTION = (
    "You are the academic assistant of the EEE department at SUST. Answer the "
    "student's question using ONLY the numbered context passages provided. If "
    "the passages do not contain the answer, say that the department library "
    "does not cover it yet and suggest asking the course teacher. Cite the "
    "passages you used as [1], [2] and so on. Never invent a formula, a "
    "citation or a page number."
)


# Words that carry no retrieval signal in a question. Kept short and generic:
# an EEE-specific stoplist would be a maintenance burden for little gain.
_STOPWORDS = {
    "the", "and", "for", "with", "what", "when", "where", "which", "who", "why",
    "how", "does", "did", "are", "was", "were", "can", "could", "should", "would",
    "this", "that", "these", "those", "from", "into", "about", "tell", "explain",
    "define", "describe", "give", "list", "difference", "between", "please", "you",
    "your", "its", "his", "her", "them", "they", "there", "here", "not", "but",
}


def _query_terms(query: str, limit: int = 8) -> list[str]:
    """Significant lowercase terms from a question, longest first."""
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9\-]*", query.lower())
    terms = [word for word in words if len(word) > 2 and word not in _STOPWORDS]
    # Longest terms are the most specific ("synchronous" beats "slip"), and the
    # cap keeps the generated CASE expression bounded.
    unique = sorted(set(terms), key=len, reverse=True)[:limit]
    return unique


class AIRagService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── retrieval ───────────────────────────────────────────────────────────

    async def _retrieve(self, query: str, course_code: str | None) -> list[tuple[str, str, str | None]]:
        """Return [(chunk_text, document_title, course_code)] for a question."""
        top_k = settings.AI_RETRIEVAL_TOP_K

        embedding = await gemini_client.embed_text(query)
        if embedding is not None:
            rows = await self._vector_search(embedding, course_code, top_k)
            if rows:
                return rows

        rows = await self._text_search(query, course_code, top_k)
        return rows

    async def _vector_search(
        self, embedding: list[float], course_code: str | None, top_k: int
    ) -> list[tuple[str, str, str | None]]:
        """Cosine-nearest chunks, filtered by course when one was named.

        Expressed with expression-language operators rather than the pgvector
        Python package: `<=>` is the cosine-distance operator, and casting the
        query vector needs only the literal type name. Wrapped in a broad
        except because SQLite (tests) and a Postgres without the vector
        extension both raise here -- retrieval then falls back to full text.
        """
        try:
            # CAST(:param AS vector(768)) -- an untyped parameter cannot
            # resolve the `<=>` operator, so the cast is required.
            distance = DocumentChunk.embedding.op("<=>")(
                cast(embedding, Vector(768))
            )
            stmt = (
                select(
                    DocumentChunk.content,
                    KnowledgeDocument.title,
                    Course.course_code,
                )
                .join(KnowledgeDocument, KnowledgeDocument.id == DocumentChunk.document_id)
                .join(Course, Course.id == KnowledgeDocument.course_id, isouter=True)
                .where(DocumentChunk.embedding.isnot(None))
                .order_by(distance)
                .limit(top_k)
            )
            if course_code:
                stmt = stmt.where(Course.course_code == course_code)
            # Savepoint, not a plain execute: on a dialect without pgvector the
            # statement fails, and a full session rollback would *expire every
            # object in the session*, so the very next attribute access (for
            # example `user.id` while persisting the exchange) raises
            # MissingGreenlet. A savepoint contains the failure instead.
            async with self.db.begin_nested():
                rows = (await self.db.execute(stmt)).all()
            return [tuple(row) for row in rows]
        except (ProgrammingError, OperationalError, SQLAlchemyError):
            return []

    async def _text_search(
        self, query: str, course_code: str | None, top_k: int
    ) -> list[tuple[str, str, str | None]]:
        """Full-text search over chunk content; ILIKE when tsvector is absent."""
        base = (
            select(DocumentChunk.content, KnowledgeDocument.title, Course.course_code)
            .join(KnowledgeDocument, KnowledgeDocument.id == DocumentChunk.document_id)
            .join(Course, Course.id == KnowledgeDocument.course_id, isouter=True)
        )
        try:
            tsv = literal_column("document_chunks.tsv_content")
            stmt = base.where(tsv.op("@@")(literal_column("plainto_tsquery('english', :q)")))
            stmt = stmt.params(q=query).limit(top_k)
            async with self.db.begin_nested():
                rows = (await self.db.execute(stmt)).all()
            return [tuple(row) for row in rows]
        except (ProgrammingError, OperationalError, SQLAlchemyError):
            pass

        # Keyword fallback. Matching the whole question as one substring only
        # works when the student happens to type a phrase that appears
        # verbatim in a document -- "What is slip?" would match nothing. Each
        # significant term is matched separately and the passages containing
        # more of them rank first, which is a crude but honest stand-in for the
        # ranking Postgres does with ts_rank.
        terms = _query_terms(query)
        if not terms:
            return []
        try:
            matches = [
                case((DocumentChunk.content.ilike(f"%{term}%", escape="\\"), 1), else_=0)
                for term in terms
            ]
            score = matches[0]
            for extra in matches[1:]:
                score = score + extra
            stmt = base.where(score > 0)
            if course_code:
                stmt = stmt.where(Course.course_code == course_code)
            stmt = stmt.order_by(score.desc()).limit(top_k)
            async with self.db.begin_nested():
                rows = (await self.db.execute(stmt)).all()
            return [tuple(row) for row in rows]
        except SQLAlchemyError:
            return []

    # ── answering ───────────────────────────────────────────────────────────

    async def answer_academic_query(
        self, user: User, prompt: str, course_code: str | None = None
    ) -> AIAnswerResponse:
        question = prompt.strip()[:1000]
        passages = await self._retrieve(question, course_code)

        citation_payload: list[AICitation] = []
        seen_titles: set[str] = set()
        for text, title, code in passages:
            if title in seen_titles:
                continue
            seen_titles.add(title)
            citation_payload.append(
                AICitation(
                    document_title=title,
                    course_code=code,
                    snippet=text[:280],
                )
            )

        if not passages:
            answer = (
                "The department library has no indexed material matching that "
                "question yet, so I will not guess. Try a different wording, or "
                "ask your course teacher."
            )
            grounded = False
            mode = "no-context"
        else:
            answer, mode = await self._compose(question, passages)
            grounded = mode == "gemini"

        session = await self._session_for(user)
        self.db.add(
            AIChatMessage(session_id=session.id, sender="student", content=question)
        )
        self.db.add(
            AIChatMessage(session_id=session.id, sender="assistant", content=answer[:2000])
        )
        await self.db.commit()

        return AIAnswerResponse(
            answer=answer,
            citations=citation_payload,
            grounded=grounded,
            mode=mode,
            session_id=session.id,
        )

    async def _compose(
        self, question: str, passages: list[tuple[str, str, str | None]]
    ) -> tuple[str, str]:
        numbered = "\n\n".join(
            f"[{index}] ({code or 'department'}) {title}: {text}"
            for index, (text, title, code) in enumerate(passages, start=1)
        )
        prompt = (
            f"Context passages:\n{numbered}\n\n"
            f"Student question: {question}\n\n"
            "Answer in at most 200 words, citing passages as [1], [2]."
        )
        generated = await gemini_client.generate_text(prompt, system=_SYSTEM_INSTRUCTION)
        if generated:
            return generated, "gemini"

        # Extractive fallback: quote the best-matching passage instead of
        # fabricating prose. Labelled in the response so the UI can say
        # "from the library" rather than implying a model wrote it.
        best_text, best_title, _ = passages[0]
        excerpt = best_text.strip().replace("\n", " ")
        if len(excerpt) > 600:
            excerpt = excerpt[:600].rsplit(" ", 1)[0] + "…"
        return (
            f"From “{best_title}”: {excerpt}\n\n"
            "(Answer assembled directly from the course library; no language "
            "model is configured on this deployment.)",
            "extractive",
        )

    async def _session_for(self, user: User) -> AIChatSession:
        session = (
            await self.db.execute(
                select(AIChatSession)
                .where(AIChatSession.student_id == user.id)
                .order_by(AIChatSession.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if session:
            return session
        session = AIChatSession(student_id=user.id, session_title="Course Q&A")
        self.db.add(session)
        await self.db.flush()
        return session

    # ── history ─────────────────────────────────────────────────────────────

    async def history(self, user: User, limit: int = 50) -> list[AIHistoryMessage]:
        session = (
            await self.db.execute(
                select(AIChatSession)
                .where(AIChatSession.student_id == user.id)
                .order_by(AIChatSession.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if not session:
            return []
        rows = (
            await self.db.execute(
                select(AIChatMessage)
                .where(AIChatMessage.session_id == session.id)
                .order_by(AIChatMessage.id.desc())
                .limit(limit)
            )
        ).scalars().all()
        return [
            AIHistoryMessage(role=row.sender, content=row.content, created_at=row.created_at)
            for row in reversed(rows)
        ]


# ── chunking ────────────────────────────────────────────────────────────────
#
# Lives here (rather than only in the Celery task) so the API can chunk a
# pasted document synchronously and so the behaviour is unit-testable. The
# ingestion task imports it.

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200


def split_into_chunks(
    text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP
) -> list[str]:
    """Split text into overlapping windows, preferring paragraph boundaries."""
    cleaned = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if not cleaned:
        return []
    if len(cleaned) <= size:
        return [cleaned]

    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(start + size, len(cleaned))
        window = cleaned[start:end]
        if end < len(cleaned):
            # Cut at the last paragraph break that keeps most of the window;
            # fall back to the hard boundary when the window has none.
            break_at = window.rfind("\n\n")
            if break_at > size // 2:
                window = window[:break_at]
                end = start + break_at
        chunks.append(window.strip())
        if end >= len(cleaned):
            break
        start = max(end - overlap, start + 1)
    return [chunk for chunk in chunks if chunk]


# Kept for the ingestion task: embedding for a single chunk, stored as the
# pgvector literal. Nullable column, so a None embedding is a valid state.
def embedding_literal(values: list[float] | None) -> str | None:
    if values is None:
        return None
    return json.dumps([float(v) for v in values])
