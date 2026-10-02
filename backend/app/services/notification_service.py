import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notification import (
    Notification,
    NotificationPreference,
    UserDevice,
)
from app.integrations.firebase_client import dispatch_push_notification


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_device(self, user_id: uuid.UUID, fcm_token: str, platform: str = "web") -> UserDevice:
        """Upsert an FCM device token for the user (idempotent per token)."""
        stmt = select(UserDevice).where(UserDevice.fcm_token == fcm_token)
        device = (await self.db.execute(stmt)).scalar_one_or_none()
        if device:
            # Re-registering an existing token re-activates it.
            device.is_active = True
            device.platform = platform
            device.user_id = user_id
        else:
            device = UserDevice(user_id=user_id, fcm_token=fcm_token, platform=platform)
            self.db.add(device)
        pref = (await self.db.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        )).scalar_one_or_none()
        if not pref:
            self.db.add(NotificationPreference(user_id=user_id))
        await self.db.commit()
        return device

    async def list_for_user(self, user_id: uuid.UUID) -> list[Notification]:
        stmt = (
            select(Notification)
            .where(Notification.recipient_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(100)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def send_10m_alert(self, fcm_token: str, course_code: str, room: str):
        return dispatch_push_notification(
            token=fcm_token,
            title=f"Class Alert: {course_code}",
            body=f"Your lecture starts in 10 minutes at {room}.",
        )

    async def notify_user(
        self, user_id: uuid.UUID, title: str, body: str, data: dict | None = None
    ) -> Notification:
        """Persist an in-app notification and push it to the user's devices.

        Persisting first means the notification is not lost if FCM is
        unreachable or unconfigured; the push is best-effort and a rejected
        token is deactivated rather than retried forever.
        """
        notification = Notification(
            recipient_id=user_id,
            title=title[:200],
            body=body[:500],
            data_payload=data or {},
        )
        self.db.add(notification)

        if await self._push_enabled(user_id):
            for device in await self._active_devices(user_id):
                delivered = dispatch_push_notification(
                    token=device.fcm_token, title=title, body=body, data=data
                )
                if delivered:
                    notification.notified_at = datetime.now(timezone.utc)
                else:
                    device.is_active = False

        await self.db.commit()
        return notification

    async def _push_enabled(self, user_id: uuid.UUID) -> bool:
        pref = (
            await self.db.execute(
                select(NotificationPreference).where(NotificationPreference.user_id == user_id)
            )
        ).scalar_one_or_none()
        return True if pref is None else bool(pref.enable_push)

    async def _active_devices(self, user_id: uuid.UUID) -> list[UserDevice]:
        rows = (
            await self.db.execute(
                select(UserDevice).where(
                    UserDevice.user_id == user_id, UserDevice.is_active.is_(True)
                )
            )
        ).scalars().all()
        return list(rows)