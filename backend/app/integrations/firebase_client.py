import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


def dispatch_push_notification(token: str, title: str, body: str):
    """Send an FCM push notification.

    Real delivery requires firebase-admin plus a service-account file. The
    portal ships without either, so this reports honestly whether a message
    was actually delivered instead of pretending success. Callers can treat
    ``False`` as "not sent" rather than assuming the user was notified.
    """
    credentials_path = settings.FIREBASE_CREDENTIALS_PATH
    if not credentials_path:
        logger.warning(
            "FCM push skipped: FIREBASE_CREDENTIALS_PATH is not configured (to=%s...)", token[:10]
        )
        return False

    try:
        import firebase_admin
        from firebase_admin import credentials, messaging
    except ImportError:
        logger.warning("FCM push skipped: firebase-admin is not installed (to=%s...)", token[:10])
        return False

    try:
        if not firebase_admin._apps:
            firebase_admin.initialize_app(credentials.Certificate(credentials_path))
        messaging.send(
            messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                token=token,
            )
        )
        return True
    except Exception:
        logger.exception("FCM push failed (to=%s...)", token[:10])
        return False
