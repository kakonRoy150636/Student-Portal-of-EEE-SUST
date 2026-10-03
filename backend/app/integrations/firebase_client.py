"""FCM HTTP v1 delivery with deliberately conservative retry classification."""

from collections.abc import Mapping
from threading import Lock

from app.core.config import settings

HTTP_TIMEOUT_SECONDS = 10
_initialization_lock = Lock()
_configured_app = None


class FCMError(RuntimeError):
    """A sanitized delivery failure; never contains a token or provider response."""


class InvalidDeviceToken(FCMError):
    """FCM explicitly reports that the registration is no longer valid."""


class RetryableFCMError(FCMError):
    """The provider explicitly rejected the request temporarily."""


class AmbiguousFCMError(FCMError):
    """Acceptance is unknown. Automatic retry could deliver a duplicate."""


class PermanentFCMError(FCMError):
    """A non-retryable error that does not justify deleting a device token."""


class FCMConfigurationError(PermanentFCMError):
    """The SDK, project, credentials, or transport needs operator attention."""


def _get_app(firebase_admin, credentials, messaging):
    global _configured_app

    # Both the second get_app and transport setup are inside the lock. Never
    # inspect firebase_admin._apps: initialization may race with another thread.
    with _initialization_lock:
        try:
            app = firebase_admin.get_app()
        except ValueError:
            credential = (
                credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
                if settings.FIREBASE_CREDENTIALS_PATH
                else credentials.ApplicationDefault()
            )
            try:
                app = firebase_admin.initialize_app(
                    credential, options={"httpTimeout": HTTP_TIMEOUT_SECONDS}
                )
            except ValueError:
                # Also tolerate another SDK consumer initializing outside our lock.
                app = firebase_admin.get_app()

        if _configured_app is not app:
            # firebase-admin retries POST read failures by default, which can
            # duplicate a push before our caller sees an ambiguous result. The
            # public send API has no retry option, so isolate this SDK adapter
            # seam here; an incompatible SDK fails closed before sending.
            from requests.adapters import HTTPAdapter

            client = messaging._get_messaging_service(app)._client
            client._timeout = HTTP_TIMEOUT_SECONDS
            client.session.mount("https://", HTTPAdapter(max_retries=0))
            client.session.mount("http://", HTTPAdapter(max_retries=0))
            _configured_app = app
        return app


def _invalid_registration_field(error) -> bool:
    """Only an explicit token-field violation authorizes deleting a token.

    INVALID_ARGUMENT alone also covers malformed notification payloads.
    """
    try:
        details = error.http_response.json()["error"]["details"]
        fields = [violation.get("field") for detail in details
                  if detail.get("@type") == "type.googleapis.com/google.rpc.BadRequest"
                  for violation in detail.get("fieldViolations", [])]
        return bool(fields) and all(field == "message.token" for field in fields)
    except (AttributeError, KeyError, TypeError, ValueError):
        return False


def dispatch_push_notification(
    token: str,
    title: str,
    body: str,
    *,
    data: Mapping[str, str] | None = None,
    priority: str = "high",
) -> str:
    """Return FCM's message ID (accepted, not proof of device delivery).

    Only InvalidDeviceToken authorizes removal of a stored registration. All
    exceptions have fixed, safe messages and suppress raw SDK exception chains.
    """
    if not isinstance(token, str) or not token.strip():
        raise PermanentFCMError("FCM registration is missing or malformed")
    if not isinstance(title, str) or not isinstance(body, str):
        raise PermanentFCMError("FCM notification fields must be strings")
    if priority not in ("high", "normal"):
        raise PermanentFCMError("FCM priority must be high or normal")
    if data is not None and (
        not isinstance(data, Mapping)
        or any(not isinstance(k, str) or not isinstance(v, str) for k, v in data.items())
    ):
        raise PermanentFCMError("FCM data must contain string keys and values")

    try:
        import firebase_admin
        from firebase_admin import credentials, exceptions, messaging
        from google.auth.exceptions import GoogleAuthError
        from requests.exceptions import RequestException

        app = _get_app(firebase_admin, credentials, messaging)
    except Exception:
        raise FCMConfigurationError("FCM initialization failed") from None

    try:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            token=token,
            data=dict(data) if data is not None else None,
            android=messaging.AndroidConfig(priority=priority),
            webpush=messaging.WebpushConfig(headers={"Urgency": priority}),
            apns=messaging.APNSConfig(headers={"apns-priority": "10" if priority == "high" else "5"}),
        )
        message_id = messaging.send(message, app=app)
    except messaging.UnregisteredError:
        raise InvalidDeviceToken("FCM registration is no longer valid") from None
    except (exceptions.DeadlineExceededError, RequestException, TimeoutError):
        raise AmbiguousFCMError("FCM delivery outcome is unknown") from None
    except (messaging.QuotaExceededError, exceptions.ResourceExhaustedError):
        raise RetryableFCMError("FCM temporarily rejected delivery") from None
    except (exceptions.UnavailableError, exceptions.InternalError) as error:
        # The SDK also wraps network connection failures as UnavailableError.
        # Only a provider response (or a provider error without a transport
        # cause) is a confirmed rejection, rather than uncertain acceptance.
        if error.http_response is None and error.cause is not None:
            raise AmbiguousFCMError("FCM delivery outcome is unknown") from None
        raise RetryableFCMError("FCM temporarily rejected delivery") from None
    except (
        GoogleAuthError,
        exceptions.UnauthenticatedError,
        exceptions.PermissionDeniedError,
        messaging.ThirdPartyAuthError,
        messaging.SenderIdMismatchError,
    ):
        raise FCMConfigurationError("FCM authentication or project configuration failed") from None
    except exceptions.InvalidArgumentError as error:
        if _invalid_registration_field(error):
            raise InvalidDeviceToken("FCM registration is invalid") from None
        raise PermanentFCMError("FCM rejected the request configuration or payload") from None
    except (
        exceptions.FailedPreconditionError,
        exceptions.NotFoundError,
        ValueError,
        TypeError,
    ):
        # INVALID_ARGUMENT may mean a payload error, not a bad registration.
        raise PermanentFCMError("FCM rejected the request configuration or payload") from None
    except Exception:
        raise AmbiguousFCMError("FCM delivery outcome is unknown") from None

    if not isinstance(message_id, str) or not message_id:
        raise AmbiguousFCMError("FCM did not return a delivery receipt")
    return message_id
