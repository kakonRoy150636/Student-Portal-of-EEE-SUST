"""Scheduled notification work.

``scan_upcoming_class_alerts`` used to be ``print("Celery: Scanning ...")``.
It now does what the name says:

1. Find today's class sessions whose start time is within the next ten
   minutes (in the deployment's timezone -- Dhaka by default, so the scan does
   not depend on the worker's clock being set to the campus timezone).
2. Resolve the students enrolled in each of those offerings who have class
   alerts enabled.
3. Write one ``notifications`` row per (recipient, session) -- the unique
   constraint from migration 007 makes this idempotent, so a beat tick that
   overlaps the previous one cannot double-send.
4. Push to that student's active devices through FCM, deactivating tokens the
   service rejects as permanently invalid.

The task is sync (Celery) around an async coroutine, like the ingestion task.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import structlog
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.integrations.firebase_client import dispatch_push_notification
from app.models.academic import ClassSchedule, Course, CourseEnrollment, CourseOffering
from app.models.facility import Room
from app.models.notification import Notification, NotificationPreference, UserDevice

logger = structlog.get_logger(__name__)

ALERT_WINDOW_MINUTES = 10


async def _devices_for(db, user_id) -> list[UserDevice]:
    rows = (
        await db.execute(
            select(UserDevice).where(
                UserDevice.user_id == user_id, UserDevice.is_active.is_(True)
            )
        )
    ).scalars().all()
    return list(rows)


async def _preferences_allow(db, user_id) -> bool:
    pref = (
        await db.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        )
    ).scalar_one_or_none()
    # No row means defaults, and the default for class alerts is on.
    return True if pref is None else bool(pref.enable_push and pref.enable_10m_class_alert)


async def _scan() -> dict:
    now = datetime.now(ZoneInfo(settings.TIMEZONE))
    window_end = now + timedelta(minutes=ALERT_WINDOW_MINUTES)
    today_name = now.strftime("%A")

    sent = 0
    considered = 0
    async with AsyncSessionLocal() as db:
        sessions = (
            await db.execute(
                select(
                    ClassSchedule.id,
                    ClassSchedule.start_time,
                    Course.course_code,
                    Room.room_number,
                )
                .join(CourseOffering, CourseOffering.id == ClassSchedule.course_offering_id)
                .join(Course, Course.id == CourseOffering.course_id)
                .join(Room, Room.id == ClassSchedule.room_id, isouter=True)
                .where(ClassSchedule.day_of_week.ilike(today_name))
            )
        ).all()

        for schedule_id, start_time, course_code, room_number in sessions:
            # ClassSchedule.start_time is a wall-clock TIME in campus time,
            # which is what the routine is published in.
            start = now.replace(
                hour=start_time.hour, minute=start_time.minute, second=0, microsecond=0
            )
            if not (now <= start <= window_end):
                continue
            considered += 1

            student_ids = (
                await db.execute(
                    select(CourseEnrollment.student_id)
                    .join(
                        ClassSchedule,
                        ClassSchedule.course_offering_id == CourseEnrollment.course_offering_id,
                    )
                    .where(
                        ClassSchedule.id == schedule_id,
                        CourseEnrollment.status != "drop",
                    )
                )
            ).scalars().all()

            title = f"Class in {ALERT_WINDOW_MINUTES} minutes: {course_code}"
            body = f"{course_code} starts at {start.strftime('%I:%M %p').lstrip('0')}"
            if room_number:
                body += f" in {room_number}"
            body += "."

            for student_id in set(student_ids):
                if not await _preferences_allow(db, student_id):
                    continue
                # Idempotency is enforced by uq_notification_class_session; the
                # pre-check avoids a rollback per already-notified student.
                already = (
                    await db.execute(
                        select(Notification.id).where(
                            Notification.recipient_id == student_id,
                            Notification.class_session_id == schedule_id,
                        )
                    )
                ).first()
                if already:
                    continue

                db.add(
                    Notification(
                        recipient_id=student_id,
                        title=title[:200],
                        body=body[:500],
                        data_payload={"course_code": course_code, "schedule_id": str(schedule_id)},
                        class_session_id=schedule_id,
                    )
                )
                try:
                    await db.flush()
                except IntegrityError:
                    await db.rollback()
                    continue

                for device in await _devices_for(db, student_id):
                    ok = dispatch_push_notification(
                        token=device.fcm_token,
                        title=title,
                        body=body,
                        data={"schedule_id": str(schedule_id)},
                    )
                    if not ok:
                        # A token FCM refuses stays in the table but stops being
                        # selected; a stale token must not be retried forever.
                        device.is_active = False
                    else:
                        sent += 1

        await db.commit()

    logger.info("class_alert_scan_complete", sessions=considered, pushes=sent)
    return {"sessions_in_window": considered, "pushes_sent": sent}


@celery_app.task(name="app.tasks.notifications.scan_upcoming_class_alerts")
def scan_upcoming_class_alerts() -> dict:
    return asyncio.run(_scan())


async def _orphan_sweep() -> dict:
    """Delete pending resource rows (and objects) left by interrupted uploads."""
    from app.services.resource_service import ResourceService

    async with AsyncSessionLocal() as db:
        removed = await ResourceService(db).purge_orphans(older_than_minutes=60)
    return {"orphaned_resources_removed": removed}


@celery_app.task(name="app.tasks.notifications.sweep_orphaned_uploads")
def sweep_orphaned_uploads() -> dict:
    return asyncio.run(_orphan_sweep())
