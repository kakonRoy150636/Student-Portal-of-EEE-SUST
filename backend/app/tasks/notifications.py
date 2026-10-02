import logging
from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)

@celery_app.task
def scan_upcoming_class_alerts():
    logger.info("Scanning 10-minute upcoming class alerts for SUST EEE students")
