"""Delivery state machine: durable claims before FCM, no ambiguous resends."""
import asyncio
from datetime import timedelta

from sqlalchemy import delete, func, select

from app.integrations.firebase_client import (
    dispatch_push_notification, InvalidDeviceToken, RetryableFCMError,
    AmbiguousFCMError, PermanentFCMError,
)
from app.models.notification import (
    DeviceToken, NotificationBatch, NotificationDelivery, NotificationLog,
    NotificationPreference, UserDevice,
)
from app.models.user import User
from app.services.notification_service import TEMPLATES, channels, next_push_time, utcnow

MAX_ATTEMPTS = 6
UNCERTAIN_AFTER = timedelta(minutes=5)


async def deliver_batch(sessions, batch_id, now=None, sender=None):
    now = now or utcnow()
    sender = sender or dispatch_push_notification
    retry_needed = False
    while True:
        async with sessions() as db, db.begin():
            batch = await db.scalar(select(NotificationBatch).where(NotificationBatch.id == batch_id).with_for_update())
            if batch is None or batch.status == "complete" or batch.due_at > now:
                return
            user = await db.get(User, batch.user_id)
            pref = await db.get(NotificationPreference, batch.user_id)
            allowed = user is not None and user.is_active and channels(pref, batch.type)[0]
            due = next_push_time(pref, now)
            if allowed and due > now:
                batch.due_at = due
                return
            deliveries = list((await db.scalars(select(NotificationDelivery).where(
                NotificationDelivery.batch_id == batch_id).with_for_update())).all())
            for item in deliveries:
                if item.status == "inflight" and item.attempted_at + UNCERTAIN_AFTER <= now:
                    item.status, item.last_error = "unknown", "worker_interrupted"
                if item.status == "pending" and not allowed:
                    item.status = "suppressed"
            pending = [d for d in deliveries if d.status == "pending"]
            ready = next((d for d in pending if d.next_attempt_at <= now), None)
            if ready is None:
                waiting = [d.next_attempt_at for d in pending]
                waiting += [d.attempted_at + UNCERTAIN_AFTER for d in deliveries if d.status == "inflight"]
                if waiting:
                    batch.due_at = min(waiting)
                else:
                    batch.status = "complete"
                    for log in (await db.scalars(select(NotificationLog).where(NotificationLog.batch_id == batch_id))).all():
                        log.status = "complete"
                break
            device = await db.get(DeviceToken, ready.device_id) if ready.device_id else None
            if device is None or device.user_id != batch.user_id:
                ready.status = "invalid"
                continue
            if ready.attempts >= MAX_ATTEMPTS:
                ready.status = "failed"
                continue
            ready.status = "inflight"
            ready.attempted_at = now
            ready.attempts += 1
            delivery_id, device_id, token = ready.id, device.id, device.token
            attempts, priority, type_ = ready.attempts, batch.priority, batch.type
            count = await db.scalar(select(func.count()).select_from(NotificationLog).where(NotificationLog.batch_id == batch_id))
        # Claim is COMMITTED before the network call. Concurrent tasks skip it.
        title, body = TEMPLATES[type_]
        if priority == "medium":
            title, body = "Portal summary", f"You have {count} new {type_.replace('_', ' ')} updates. Open the portal for details."
        outcome, error = "sent", None
        try:
            await asyncio.to_thread(sender, token, title, body, data={"type": type_, "notification_id": str(batch_id)},
                                    priority="high" if priority == "high" else "normal")
        except InvalidDeviceToken:
            outcome, error = "invalid", "unregistered"
        except RetryableFCMError:
            outcome, error = ("pending" if attempts < MAX_ATTEMPTS else "failed"), "retryable"
            retry_needed = retry_needed or outcome == "pending"
        except AmbiguousFCMError:
            outcome, error = "unknown", "ambiguous"
        except PermanentFCMError:
            outcome, error = "failed", "configuration_or_payload"
        except Exception:
            # Never retry an unclassified exception after a send may have begun.
            outcome, error = "unknown", "unclassified"
        async with sessions() as db, db.begin():
            item = await db.get(NotificationDelivery, delivery_id)
            item.status, item.last_error = outcome, error
            if outcome == "pending":
                item.next_attempt_at = now + timedelta(seconds=min(60 * 2 ** (attempts - 1), 3600))
            if outcome == "invalid":
                await db.execute(delete(DeviceToken).where(DeviceToken.id == device_id, DeviceToken.token == token))
                await db.execute(delete(UserDevice).where(UserDevice.fcm_token == token))
    if retry_needed:
        raise RetryableFCMError("Confirmed transient FCM rejection")
