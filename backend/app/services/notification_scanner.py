import uuid
from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import select, text

from app.models.academic import ClassSchedule, CourseOffering, CourseEnrollment, Semester
from app.models.user import User
from app.models.notification import NotificationLog, NotificationPreference
from app.services.notification_service import NotificationService, DHAKA, channels, next_push_time, utcnow

OCCURRENCE_NAMESPACE = uuid.UUID("f2695e1e-2cbd-4dcb-8fba-3ac6f36cf774")


async def scan_classes(db, now=None):
    now = now or utcnow()
    local = now.astimezone(DHAKA)
    end = local + timedelta(minutes=10)
    created, batches = 0, []
    for day in sorted({local.date(), end.date()}):
        day_name = day.strftime("%A")
        lower = local.time().replace(tzinfo=None) if day == local.date() else datetime.min.time()
        upper = end.time().replace(tzinfo=None) if day == end.date() else datetime.max.time()
        query = select(ClassSchedule.id, ClassSchedule.start_time, User.id).join(
            CourseOffering, ClassSchedule.course_offering_id == CourseOffering.id
        ).join(Semester, CourseOffering.semester_id == Semester.id).join(
            CourseEnrollment, CourseEnrollment.course_offering_id == CourseOffering.id
        ).join(User, CourseEnrollment.student_id == User.id).where(
            ClassSchedule.day_of_week.in_([day_name, day_name.lower(), day_name[:3], day_name[:3].lower()]),
            ClassSchedule.start_time >= lower, ClassSchedule.start_time <= upper,
            Semester.is_active.is_(True), Semester.start_date <= day, Semester.end_date >= day,
            User.is_active.is_(True), CourseEnrollment.status.in_(["enrolled", "main", "improvement"]),
        )
        for schedule_id, start, user_id in (await db.execute(query)).all():
            occurrence = uuid.uuid5(OCCURRENCE_NAMESPACE, f"{schedule_id}:{day.isoformat()}")
            result = await NotificationService(db).enqueue(user_id, occurrence, "class_reminder", "high", now)
            if result:
                created += 1
                if result[1]:
                    batches.append(result[1])
    return created, batches


async def group_digest(db, now=None):
    now = now or utcnow()
    # Serialize grouping, independent of Beat count or duplicate worker tasks.
    if not await db.scalar(text("SELECT pg_try_advisory_xact_lock(736887202)")):
        return []
    logs = list((await db.scalars(select(NotificationLog).where(
        NotificationLog.status == "pending", NotificationLog.priority == "medium",
        NotificationLog.due_at <= now,
    ).order_by(NotificationLog.created_at).with_for_update())).all())
    groups = defaultdict(list)
    for log in logs:
        pref = await db.get(NotificationPreference, log.user_id)
        if not channels(pref, log.type)[0]:
            log.status = "complete"
            continue
        due = next_push_time(pref, now)
        if due > now:
            log.due_at = due
            continue
        groups[(log.user_id, log.type)].append(log)
    return [await NotificationService(db).make_batch(items, now) for items in groups.values()]
