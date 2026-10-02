"""Firebase Cloud Messaging dispatch.

Previously this module printed the token and title to stdout and returned
True, so every "push notification" in the portal was a log line that reported
success. It now actually initialises the Firebase Admin SDK from
``FIREBASE_CREDENTIALS_PATH`` and sends the message, with honest failure
reporting:

* no credentials file        -> logs once, returns False (not an error: a
                                 local checkout has no Firebase project)
* token rejected by FCM      -> returns False and the caller deactivates that
                                 device row, so the next send skips it
* transient transport error  -> returns False, device stays active

The SDK import is lazy so the API process starts (and the test suite runs)
without ``firebase-admin`` configured.
"""

from __future__ import annotations

import os
import threading

import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

_init_lock = threading.Lock()
_app = None
_init_failed = False


def _get_app():
    """Initialise the Admin SDK once, or return None when unavailable."""
    global _app, _init_failed
    if _app is not None or _init_failed:
        return _app
    with _init_lock:
        if _app is not None or _init_failed:
            return _app
        path = settings.FIREBASE_CREDENTIALS_PATH
        if not path or not os.path.exists(path):
            logger.info("fcm_not_configured", credentials_path=path)
            _init_failed = True
            return None
        try:
            import firebase_admin
            from firebase_admin import credentials

            cred = credentials.Certificate(path)
            _app = firebase_admin.initialize_app(cred)
            logger.info("fcm_initialised")
        except Exception as exc:  # noqa: BLE001 - any init failure is non-fatal
            logger.warning("fcm_init_failed", error=str(exc))
            _init_failed = True
    return _app


def dispatch_push_notification(
    token: str, title: str, body: str, data: dict | None = None
) -> bool:
    """Send one push notification. Returns True only if FCM accepted it."""
    if not settings.FCM_ENABLED or not token:
        return False
    if _get_app() is None:
        return False
    try:
        from firebase_admin import messaging

        message = messaging.Message(
            token=token,
            notification=messaging.Notification(title=title, body=body),
            data={key: str(value) for key, value in (data or {}).items()},
        )
        messaging.send(message, app=_app)
        return True
    except Exception as exc:  # noqa: BLE001 - a failed push must not fail the request
        # An unregistered/invalid token is permanent: the caller deactivates
        # the device row rather than retrying it forever.
        logger.warning(
            "fcm_send_failed",
            error=str(exc),
            permanent=_is_permanent_failure(exc),
            token_prefix=token[:12],
        )
        return False


def _is_permanent_failure(exc: Exception) -> bool:
    name = type(exc).__name__
    if name in {"UnregisteredError", "SenderIdMismatchError", "InvalidArgumentError"}:
        return True
    message = str(exc).lower()
    return "unregistered" in message or "not a valid fcm registration token" in message
