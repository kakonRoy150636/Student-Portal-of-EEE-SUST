"""Private-by-construction notification inbox, preferences and durable outbox."""
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import (
    DeviceToken, Notification, NotificationBatch, NotificationDelivery,
    NotificationLog, NotificationPreference,
)
from app.models.user import User

DHAKA = ZoneInfo("Asia/Dhaka")
TEMPLATES = {
    "class_reminder": ("Class reminder", "You have a class reminder. Open the portal for details."),
    "lab_reminder": ("Lab reminder", "A lab activity needs your attention. Open the portal for details."),
    "exam_reminder": ("Academic reminder", "An academic event needs your attention. Open the portal for details."),
    "announcement": ("Portal update", "A new update is available. Open the portal for details."),
    "course_assignment": (
        "Course assignment update",
        "A course assignment update is available. Open the portal for details.",
    ),
    "course_enrollment": (
        "Course enrollment update",
        "Your course enrollment was updated. Open the portal for details.",
    ),
    "course_available": (
        "New course available",
        "A new course is available for selection. Open the portal for details.",
    ),
}
NOTIFICATION_URLS = {
    "class_reminder": "/schedule", "lab_reminder": "/schedule",
    "exam_reminder": "/schedule", "announcement": "/notifications",
    "course_assignment": "/notifications", "course_enrollment": "/notifications",
    "course_available": "/course-selection",
}


def insert_for(db, model):
    return (sqlite_insert if db.get_bind().dialect.name == "sqlite" else pg_insert)(model)


def utcnow():
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    """Normalize Postgres-aware and SQLite-naive timestamps for comparisons."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def channels(pref: NotificationPreference | None, type_: str) -> tuple[bool, bool]:
    if pref is None:
        return True, True
    value = (pref.per_type or {}).get(type_, {})
    legacy = {"class_reminder": pref.enable_10m_class_alert,
              "lab_reminder": pref.enable_lab_reminders, "exam_reminder": pref.enable_exam_alerts}
    return bool(pref.enable_push and legacy.get(type_, True) and value.get("push", True)), bool(value.get("in_app", True))


def next_push_time(pref: NotificationPreference | None, now: datetime) -> datetime:
    """Quiet hours suppress push (all priorities), not the in-app inbox."""
    if pref is None or pref.quiet_start is None or pref.quiet_end is None:
        return now
    local = now.astimezone(DHAKA)
    start, end, clock = pref.quiet_start, pref.quiet_end, local.time().replace(tzinfo=None)
    if start == end:  # equal endpoints mean quiet hours disabled
        return now
    quiet = start <= clock < end if start < end else clock >= start or clock < end
    if not quiet:
        return now
    day = local.date() + timedelta(days=1 if start > end and clock >= start else 0)
    return datetime.combine(day, end, tzinfo=DHAKA).astimezone(timezone.utc)


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_device(self, user_id: uuid.UUID, fcm_token: str, platform: str = "web") -> DeviceToken:
        stmt = insert_for(self.db, DeviceToken).values(user_id=user_id, token=fcm_token, platform=platform, last_seen=utcnow())
        stmt = stmt.on_conflict_do_update(index_elements=[DeviceToken.token], set_={
            "user_id": user_id, "platform": platform, "last_seen": utcnow(),
        }).returning(DeviceToken.id)
        ident = await self.db.scalar(stmt)
        await self.db.commit()
        device = await self.db.get(DeviceToken, ident)
        assert device is not None
        return device

    async def list_for_user(self, user_id: uuid.UUID) -> list[Notification]:
        return list((await self.db.scalars(select(Notification).where(
            Notification.recipient_id == user_id).order_by(Notification.created_at.desc()).limit(100))).all())

    async def get_preferences(self, user_id):
        pref = await self.db.get(NotificationPreference, user_id)
        return {
            "per_type": {type_: {"push": channels(pref, type_)[0], "in_app": channels(pref, type_)[1]} for type_ in TEMPLATES},
            "quiet_start": pref.quiet_start if pref else None,
            "quiet_end": pref.quiet_end if pref else None,
            "timezone": "Asia/Dhaka",
        }

    async def set_preferences(self, user_id, payload):
        values = {"per_type": {k: v.model_dump() for k, v in payload.per_type.items()},
                  "quiet_start": payload.quiet_start, "quiet_end": payload.quiet_end,
                  "enable_push": True, "enable_10m_class_alert": True,
                  "enable_lab_reminders": True, "enable_exam_alerts": True}
        stmt = insert_for(self.db, NotificationPreference).values(user_id=user_id, **values)
        await self.db.execute(stmt.on_conflict_do_update(index_elements=[NotificationPreference.user_id], set_=values))
        await self.db.commit()
        return await self.get_preferences(user_id)

    async def enqueue(self, user_id, event_id, type_: str, priority: str, now=None):
        """Transaction owned by caller; return (log_id, high_batch_id) or None.

        No caller-controlled title/body/data: even internal tasks cannot put
        grades, names, identifiers or arbitrary personal data into messages.
        """
        if type_ not in TEMPLATES or priority not in {"high", "medium", "low"}:
            raise ValueError("Unknown notification type or priority")
        now = now or utcnow()
        user = await self.db.get(User, user_id)
        if user is None or not user.is_active:
            return None
        pref = await self.db.get(NotificationPreference, user_id)
        push, in_app = channels(pref, type_)
        push = push and priority != "low"
        due = next_push_time(pref, now)
        if priority == "medium":
            due = max(due, now + timedelta(minutes=5))
        stmt = insert_for(self.db, NotificationLog).values(
            user_id=user_id, event_id=event_id, type=type_, priority=priority,
            status="pending" if push else "complete", due_at=due,
        ).on_conflict_do_nothing(index_elements=[NotificationLog.user_id, NotificationLog.event_id, NotificationLog.type]).returning(NotificationLog.id)
        log_id = await self.db.scalar(stmt)
        if log_id is None:
            return None
        log = await self.db.get(NotificationLog, log_id)
        assert log is not None
        if in_app:
            title, body = TEMPLATES[type_]
            notification = Notification(recipient_id=user_id, title=title, body=body,
                                        data_payload={"type": type_, "url": NOTIFICATION_URLS[type_]})
            self.db.add(notification)
            await self.db.flush()
            log.notification_id = notification.id
        batch_id = None
        if push and priority == "high":
            batch_id = await self.make_batch([log], now)
        await self.db.flush()
        return log_id, batch_id

    async def make_batch(self, logs, now):
        first = logs[0]
        batch = NotificationBatch(user_id=first.user_id, type=first.type, priority=first.priority,
                                  due_at=max(as_utc(now), max(as_utc(row.due_at) for row in logs)))
        self.db.add(batch)
        await self.db.flush()
        devices = list((await self.db.scalars(select(DeviceToken).where(DeviceToken.user_id == first.user_id))).all())
        for device in devices:
            self.db.add(NotificationDelivery(batch_id=batch.id, device_id=device.id, next_attempt_at=batch.due_at))
        for log in logs:
            log.batch_id = batch.id
            log.status = "assigned" if devices else "complete"
        if not devices:
            batch.status = "complete"
        await self.db.flush()
        return batch.id
