from app.core.celery_app import celery_app

@celery_app.task
def ingest_document_chunk(doc_id: str, content: str):
    print(f"Celery: Embedding document {doc_id} with Gemini text-embedding-004...")
