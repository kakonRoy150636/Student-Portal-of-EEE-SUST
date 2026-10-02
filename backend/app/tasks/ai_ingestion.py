import logging

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task
def ingest_document_chunk(doc_id: str, content: str):
    logger.info("Embedding document %s with Gemini text-embedding-004", doc_id)
