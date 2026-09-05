from app.core.celery_app import celery_app

@celery_app.task
def scan_upcoming_class_alerts():
    print("Celery: Scanning 10-minute upcoming class alerts for SUST EEE students...")
