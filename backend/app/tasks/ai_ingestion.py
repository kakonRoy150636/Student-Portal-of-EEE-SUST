"""Trusted operator/Celery ingestion; metadata must come from the source document."""
import asyncio
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.ai_budget import reserve_ai
from app.integrations.gemini_client import GeminiClient, embedding_cost
from app.services.ai_retrieval import sanitize_chunk, clean_text


async def ingest_chunk(sessions, document_id, content, page_number=None, section=None, *, provider=None):
    content = sanitize_chunk(content)
    section = sanitize_chunk(section) if section else None
    if not content or not (page_number or section) or (page_number is not None and page_number <= 0):
        raise ValueError("Safe source text and an authentic page/section are required")
    if len(content.encode('utf-8')) > 1800:
        raise ValueError("Split the document into smaller source chunks (maximum 1800 UTF-8 bytes)")
    if section and len(section) > 255:
        raise ValueError("Section label is too long")
    ident = str(uuid.UUID(str(document_id)))
    async with sessions() as db:
        title = await db.scalar(text("SELECT title FROM knowledge_documents WHERE id=CAST(:id AS uuid)"), {'id': ident})
        if not title or not sanitize_chunk(title):
            raise ValueError("Knowledge document not found or has an unsafe title")
        existing = await db.scalar(text("""SELECT id FROM document_chunks WHERE document_id=CAST(:id AS uuid)
            AND content=:content AND page_number IS NOT DISTINCT FROM :page
            AND section IS NOT DISTINCT FROM :section AND embedding_model=:model LIMIT 1"""),
            {'id': ident, 'content': content, 'page': page_number, 'section': section, 'model': settings.GEMINI_EMBEDDING_MODEL})
        if existing:
            return str(existing)
    reserve = await reserve_ai('knowledge-ingestion', embedding_cost(content), enforce_user_quota=False)
    vector = await (provider or GeminiClient()).embed(content, document=True)
    await reserve.settle(embedding_cost(content))
    async with sessions() as db, db.begin():
        chunk = await db.scalar(text("""INSERT INTO document_chunks(document_id,content,embedding,page_number,section,embedding_model)
            VALUES(CAST(:doc AS uuid),:content,CAST(:vector AS vector),:page,:section,:model) RETURNING id"""),
            {'doc': ident, 'content': content, 'vector': '[' + ','.join(str(x) for x in vector) + ']',
             'page': page_number, 'section': clean_text(section, 255) if section else None, 'model': settings.GEMINI_EMBEDDING_MODEL})
        return str(chunk)


@celery_app.task
def ingest_document_chunk(doc_id: str, content: str, page_number: int | None = None, section: str | None = None):
    async def work():
        engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
        try:
            return await ingest_chunk(async_sessionmaker(engine, expire_on_commit=False), doc_id, content, page_number, section)
        finally:
            await engine.dispose()
    return asyncio.run(work())
