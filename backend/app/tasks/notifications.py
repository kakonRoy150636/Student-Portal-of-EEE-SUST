"""Celery adapters; each run owns its async engine/event loop."""
import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.celery_app import celery_app
from app.core.config import settings
from app.integrations.firebase_client import RetryableFCMError
from app.models.notification import NotificationBatch
from app.services.notification_service import NotificationService, utcnow
from app.services.notification_dispatch import deliver_batch
from app.services.notification_scanner import scan_classes, group_digest


async def _with_sessions(callback):
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    try:
        return await callback(async_sessionmaker(engine, expire_on_commit=False))
    finally:
        await engine.dispose()


def _publish(batch_ids):
    for ident in batch_ids:
        deliver_notification.delay(str(ident))


@celery_app.task(autoretry_for=(RetryableFCMError,), retry_backoff=60,
                 retry_backoff_max=3600, retry_jitter=False,
                 retry_kwargs={"max_retries": 5}, acks_late=True)
def deliver_notification(batch_id: str):
    async def work(sessions):
        await deliver_batch(sessions, uuid.UUID(batch_id))
    asyncio.run(_with_sessions(work))


@celery_app.task
def create_notification(user_id: str, event_id: str, type_: str, priority: str = "high"):
    """Internal producer API: stable event ID, allowlisted type, no free text."""
    async def work(sessions):
        async with sessions() as db, db.begin():
            return await NotificationService(db).enqueue(uuid.UUID(user_id), uuid.UUID(event_id), type_, priority)
    result = asyncio.run(_with_sessions(work))
    if result and result[1]:
        _publish([result[1]])
    return str(result[0]) if result else None


@celery_app.task
def scan_upcoming_class_alerts():
    async def work(sessions):
        async with sessions() as db, db.begin():
            return await scan_classes(db)
    created, batches = asyncio.run(_with_sessions(work))
    _publish(batches)
    return {"created": created}


@celery_app.task
def digest_notifications():
    async def work(sessions):
        async with sessions() as db, db.begin():
            return await group_digest(db)
    batches = asyncio.run(_with_sessions(work))
    _publish(batches)
    return {"batches": len(batches)}


@celery_app.task
def recover_pending_notifications():
    """DB outbox recovers a broker failure between commit and task publication."""
    async def work(sessions):
        async with sessions() as db:
            return list((await db.scalars(select(NotificationBatch.id).where(
                NotificationBatch.status == "pending", NotificationBatch.due_at <= utcnow(),
            ).order_by(NotificationBatch.due_at).limit(500))).all())
    batches = asyncio.run(_with_sessions(work))
    _publish(batches)
    return {"queued": len(batches)}
