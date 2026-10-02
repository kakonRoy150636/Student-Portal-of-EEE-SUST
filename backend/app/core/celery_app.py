from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "sust_eee_scheduler",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.notifications", "app.tasks.ai_ingestion", "app.tasks.maintenance"],
)

celery_app.conf.timezone = settings.TIMEZONE
celery_app.conf.beat_schedule = {
    # Every minute: a class starting inside the next ten minutes gets one
    # alert per enrolled student (idempotent via uq_notification_class_session).
    "scan-10-minute-class-alerts": {
        "task": "app.tasks.notifications.scan_upcoming_class_alerts",
        "schedule": crontab(minute="*"),
    },
    # Hourly: delete resource rows whose upload never completed, so a crashed
    # request does not leave an object in the bucket and a row in listings.
    "sweep-orphaned-uploads": {
        "task": "app.tasks.notifications.sweep_orphaned_uploads",
        "schedule": crontab(minute=17),
    },
    # Daily at 03:40: prune dead refresh tokens and spent password-reset
    # tokens. Both tables gain a row per login/reset and previously only grew.
    "cleanup-expired-tokens": {
        "task": "app.tasks.maintenance.cleanup_expired_tokens",
        "schedule": crontab(hour=3, minute=40),
    },
}
