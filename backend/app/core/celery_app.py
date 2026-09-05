from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "sust_eee_scheduler",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.notifications", "app.tasks.ai_ingestion"],
)

celery_app.conf.timezone = "Asia/Dhaka"
celery_app.conf.beat_schedule = {
    "scan-10-minute-class-alerts": {
        "task": "app.tasks.notifications.scan_upcoming_class_alerts",
        "schedule": crontab(minute="*"),
    }
}
