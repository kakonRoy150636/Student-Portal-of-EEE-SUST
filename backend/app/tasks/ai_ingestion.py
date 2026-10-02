"""Knowledge-base ingestion.

Replaces a task whose entire body was ``print("Celery: Embedding document ...")``.
The document text is split into overlapping chunks, each chunk is embedded when
a Gemini key is configured, and the rows land in ``document_chunks`` where the
retrieval service can find them.

Chunking is character-based with a paragraph bias rather than token-based: an
exact token count needs the model's tokenizer, and the embedding API accepts
long input anyway. 1200 characters with 200 of overlap keeps a formula or a
definition from being cut in half at a boundary.
"""

from __future__ import annotations

import asyncio
import uuid

import structlog
from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.integrations import gemini_client
from app.models.ai_knowledge import DocumentChunk, KnowledgeDocument

logger = structlog.get_logger(__name__)

# Chunking lives with the retrieval service so the API and the task cannot
# drift apart; re-exported here because this module is the documented entry
# point for ingestion.
from app.services.ai_rag_service import CHUNK_OVERLAP, CHUNK_SIZE, split_into_chunks  # noqa: E402


async def _ingest(document_id: uuid.UUID, content: str) -> dict:
    async with AsyncSessionLocal() as db:
        document = (
            await db.execute(
                select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
            )
        ).scalar_one_or_none()
        if not document:
            return {"status": "missing", "document_id": str(document_id)}

        # Re-ingesting replaces the chunks: a corrected document must not leave
        # the old text searchable alongside the new.
        existing = (
            await db.execute(
                select(DocumentChunk).where(DocumentChunk.document_id == document_id)
            )
        ).scalars().all()
        for row in existing:
            await db.delete(row)

        chunks = split_into_chunks(content)
        embedded = 0
        for position, chunk in enumerate(chunks):
            values = await gemini_client.embed_text(chunk)
            if values is not None:
                embedded += 1
            db.add(
                DocumentChunk(
                    document_id=document_id,
                    content=chunk[:2000],
                    embedding=values,
                )
            )
        await db.commit()

    logger.info(
        "document_ingested",
        document_id=str(document_id),
        chunks=len(chunks),
        embedded=embedded,
    )
    return {
        "status": "ingested",
        "document_id": str(document_id),
        "chunks": len(chunks),
        "embedded": embedded,
    }


@celery_app.task(name="app.tasks.ai_ingestion.ingest_document")
def ingest_document(document_id: str, content: str) -> dict:
    """Celery entry point (sync) around the async ingestion coroutine."""
    try:
        parsed = uuid.UUID(str(document_id))
    except (TypeError, ValueError):
        return {"status": "invalid-document-id", "document_id": str(document_id)}
    return asyncio.run(_ingest(parsed, content))
