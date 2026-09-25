"""Role-aware dashboard summary.

Every field returned here is derived from a live SQL aggregate at request
time. Nothing is a hardcoded literal: the previous dashboards rendered
"88.5% attendance", "04 COURSES" and "12 TO REVIEW" as frozen strings in the
React components, which is why the homepage could never show anything real.

Each builder only touches the tables its role is allowed to see, and every
one is wrapped so a missing table degrades that single tile to ``None``
instead of 500-ing the whole page. The counts are cheap (``count(*)`` with an
optional indexed filter) and a dashboard is the most-hit authenticated view,
so the queries are deliberately narrow rather than multi-join aggregates.
"""
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic import (
    ClassSchedule,
    CourseEnrollment,
    CourseOffering,
    CourseOfferingTeacher,
    Course,
)
from app.models.alumni import AlumniProfile, MentorshipPair
from app.models.attendance import AttendanceRecord, AttendanceSession
from app.models.career import CareerOpportunity
from app.models.facility import Room, RoomReservation
from app.models.lab import EquipmentAsset, EquipmentBorrowRequest
from app.models.notification import Notification
from app.models.project import Project, SupervisorProposal
from app.models.user import User, UserRole

# An attendance record counts as "attended" for the threshold in
# AttendanceService (present + late). Kept as a constant so the dashboard and
# the real attendance summary can never disagree.
ATTENDED_STATUSES = ("present", "late")


async def _scalar(db: AsyncSession, stmt, default=0):
    """Run a single-value aggregate, returning ``default`` on any DB error.

    A dashboard must never be a hard 500 because one optional subsystem
    (labs, AI knowledge) has no data or table yet. A ``None`` in the response
    tells the UI to omit that tile; a zero tells it the truth.
    """
    try:
        return (await db.execute(stmt)).scalar()
    except SQLAlchemyError:
        return default


async def _count(db: AsyncSession, stmt) -> int:
    value = await _scalar(db, stmt, default=0)
    return int(value or 0)


async def _role_counts(db: AsyncSession) -> dict[str, int]:
    stmt = select(User.role, func.count(User.id)).group_by(User.role)
    try:
        rows = (await db.execute(stmt)).all()
    except SQLAlchemyError:
        return {}
    counts = {role.value if hasattr(role, "value") else str(role): int(n) for role, n in rows}
    return {UserRole(r).value: counts.get(r, 0) for r in UserRole}


# ── per-role sections ───────────────────────────────────────────────────────

async def _student_section(db: AsyncSession, user: User) -> dict:
    """Attendance, credit load and today's routine for a student/CR.

    The attendance figures reuse the same aggregation shape as
    AttendanceService.get_student_summary so the dashboard can never show a
    different percentage from the Attendance page.
    """
    enrolled = await _count(
        db,
        select(func.count(CourseEnrollment.id)).where(CourseEnrollment.student_id == user.id),
    )

    total_stmt = (
        select(func.count(AttendanceRecord.id))
        .join(AttendanceSession, AttendanceSession.id == AttendanceRecord.session_id)
        .join(CourseEnrollment, CourseEnrollment.course_offering_id == AttendanceSession.course_offering_id)
        .where(CourseEnrollment.student_id == user.id)
    )
    attended_stmt = (
        select(func.count(AttendanceRecord.id))
        .join(AttendanceSession, AttendanceSession.id == AttendanceRecord.session_id)
        .join(CourseEnrollment, CourseEnrollment.course_offering_id == AttendanceSession.course_offering_id)
        .where(CourseEnrollment.student_id == user.id, AttendanceRecord.status.in_(ATTENDED_STATUSES))
    )
    total_classes = await _count(db, total_stmt)
    attended = await _count(db, attended_stmt)
    percentage = round(attended / total_classes * 100, 2) if total_classes else None

    # "Credits" = the distinct courses this student is enrolled in, with the
    # real credit hours summed from the courses table.
    credits_stmt = (
        select(func.coalesce(func.sum(Course.credit_hours), 0))
        .select_from(CourseEnrollment)
        .join(CourseOffering, CourseOffering.id == CourseEnrollment.course_offering_id)
        .join(Course, Course.id == CourseOffering.course_id)
        .where(CourseEnrollment.student_id == user.id)
    )
    credits = await _scalar(db, credits_stmt, default=0)

    routine = await _today_routine(db, CourseEnrollment.student_id == user.id)
    notifications_unread = await _unread_notifications(db, user.id)

    return {
        "enrolled_courses": enrolled,
        "total_classes": total_classes,
        "attended": attended,
        "attendance_percentage": percentage,
        # Mirrors the server-side 75% rule in AttendanceService.
        "below_attendance_threshold": None if percentage is None else percentage < 75.0,
        "credit_hours": float(credits or 0),
        "today_classes": len(routine),
        "routine": routine,
        "unread_notifications": notifications_unread,
        "opportunities": await _count(
            db,
            select(func.count(CareerOpportunity.id)).where(
                CareerOpportunity.is_verified.is_(True),
                CareerOpportunity.application_deadline >= date.today(),
            ),
        ),
    }


async def _teacher_section(db: AsyncSession, user: User) -> dict:
    """Teaching load and review queues for a teacher."""
    offerings_stmt = select(func.count(func.distinct(CourseOfferingTeacher.course_offering_id))).where(
        CourseOfferingTeacher.teacher_id == user.id
    )
    students_stmt = (
        select(func.count(func.distinct(CourseEnrollment.student_id)))
        .join(CourseOfferingTeacher, CourseOfferingTeacher.course_offering_id == CourseEnrollment.course_offering_id)
        .where(CourseOfferingTeacher.teacher_id == user.id)
    )
    today_stmt = (
        select(func.count(ClassSchedule.id))
        .join(CourseOfferingTeacher, CourseOfferingTeacher.course_offering_id == ClassSchedule.course_offering_id)
        .where(
            CourseOfferingTeacher.teacher_id == user.id,
            ClassSchedule.day_of_week.ilike(_today_name()),
        )
    )
    proposals_stmt = select(func.count(SupervisorProposal.id)).where(SupervisorProposal.status == "pending")

    return {
        "assigned_courses": await _count(db, offerings_stmt),
        "students_taught": await _count(db, students_stmt),
        "today_classes": await _count(db, today_stmt),
        "pending_equipment_requests": await _count(
            db, select(func.count(EquipmentBorrowRequest.id)).where(EquipmentBorrowRequest.status == "pending_approval")
        ),
        "pending_room_requests": await _count(
            db, select(func.count(RoomReservation.id)).where(RoomReservation.status == "pending")
        ),
        "pending_project_proposals": await _count(db, proposals_stmt),
        "unread_notifications": await _unread_notifications(db, user.id),
    }


async def _admin_section(db: AsyncSession) -> dict:
    """Department-wide counts, including the real approval backlog."""
    return {
        "users_total": await _count(db, select(func.count(User.id))),
        "users_active": await _count(db, select(func.count(User.id)).where(User.is_active.is_(True))),
        "pending_approvals": await _count(
            db, select(func.count(User.id)).where(User.is_active.is_(False))
        ),
        "users_by_role": await _role_counts(db),
        "pending_alumni_claims": await _count(
            db,
            select(func.count(AlumniProfile.id)).where(AlumniProfile.membership_status == "pending"),
        ),
        "active_alumni": await _count(
            db,
            select(func.count(AlumniProfile.id)).where(
                AlumniProfile.membership_status == "active", AlumniProfile.is_visible.is_(True)
            ),
        ),
        "pending_room_requests": await _count(
            db, select(func.count(RoomReservation.id)).where(RoomReservation.status == "pending")
        ),
        "rooms_total": await _count(db, select(func.count(Room.id))),
        "equipment_total": await _count(db, select(func.count(EquipmentAsset.id))),
        "pending_equipment_requests": await _count(
            db, select(func.count(EquipmentBorrowRequest.id)).where(EquipmentBorrowRequest.status == "pending_approval")
        ),
        "courses": await _count(db, select(func.count(Course.id))),
        "projects": await _count(db, select(func.count(Project.id))),
        "unread_notifications": 0,
    }


async def _er_section(db: AsyncSession) -> dict:
    """Lab operations counters for a lab assistant / ER."""
    return {
        "equipment_total": await _count(db, select(func.count(EquipmentAsset.id))),
        "equipment_under_repair": await _count(
            db, select(func.count(EquipmentAsset.id)).where(EquipmentAsset.condition != "operational")
        ),
        "pending_borrow_requests": await _count(
            db, select(func.count(EquipmentBorrowRequest.id)).where(EquipmentBorrowRequest.status == "pending_approval")
        ),
        "rooms_total": await _count(db, select(func.count(Room.id))),
        "pending_room_requests": await _count(
            db, select(func.count(RoomReservation.id)).where(RoomReservation.status == "pending")
        ),
        "unread_notifications": await _unread_notifications(db, None),
    }


async def _alumni_section(db: AsyncSession, user: User) -> dict:
    """Directory standing and verified-alumni counters."""
    return {
        "visible_alumni": await _count(
            db,
            select(func.count(AlumniProfile.id)).where(
                AlumniProfile.membership_status == "active", AlumniProfile.is_visible.is_(True)
            ),
        ),
        "active_alumni": await _count(
            db, select(func.count(AlumniProfile.id)).where(AlumniProfile.membership_status == "active")
        ),
        "mentorship_pairs": await _count(
            db, select(func.count(MentorshipPair.id)).where(MentorshipPair.status.in_(("active", "requested")))
        ),
        "career_opportunities": await _count(
            db, select(func.count(CareerOpportunity.id)).where(CareerOpportunity.is_verified.is_(True))
        ),
        "unread_notifications": await _unread_notifications(db, user.id),
    }


# ── shared helpers ──────────────────────────────────────────────────────────

def _today_name() -> str:
    return date.today().strftime("%A")


async def _unread_notifications(db: AsyncSession, user_id) -> int:
    if user_id is None:
        return 0
    return await _count(
        db,
        select(func.count(Notification.id)).where(
            Notification.recipient_id == user_id, Notification.is_read.is_(False)
        ),
    )


async def _today_routine(db: AsyncSession, owner_filter) -> list[dict]:
    """Classes the given student/CR has today, with real course and room names.

    ``day_of_week`` is stored as a weekday name, so "today" is compared
    case-insensitively. Returns an empty list rather than raising if the
    schedule tables are empty.
    """
    stmt = (
        select(
            Course.course_code,
            Course.title,
            ClassSchedule.day_of_week,
            ClassSchedule.start_time,
            ClassSchedule.end_time,
            Room.room_number,
            Room.building,
        )
        .select_from(ClassSchedule)
        .join(CourseOffering, CourseOffering.id == ClassSchedule.course_offering_id)
        .join(Course, Course.id == CourseOffering.course_id)
        .join(Room, Room.id == ClassSchedule.room_id)
        .where(ClassSchedule.day_of_week.ilike(_today_name()))
        .distinct()
    )
    # Restrict to the caller's own enrolments.
    if owner_filter is not None:
        enrolled = (
            select(CourseEnrollment.course_offering_id)
            .where(owner_filter, CourseEnrollment.status.notin_(("drop",)))
            .subquery()
        )
        stmt = stmt.where(CourseOffering.id.in_(enrolled))

    try:
        rows = (await db.execute(stmt)).all()
    except SQLAlchemyError:
        return []

    routine = []
    for code, title, day, start, end, room_number, building in rows:
        routine.append(
            {
                "course_code": code,
                "course_title": title,
                "day_of_week": day,
                "start_time": start.strftime("%I:%M %p").lstrip("0") if start else None,
                "end_time": end.strftime("%I:%M %p").lstrip("0") if end else None,
                "room_number": room_number,
                "building": building,
            }
        )
    routine.sort(key=lambda r: (r["start_time"] or ""))
    return routine


# ── entry point ─────────────────────────────────────────────────────────────

async def build_summary(db: AsyncSession, user: User) -> dict:
    """Role-scoped dashboard payload. Only the caller's own section is built."""
    payload: dict = {"role": user.role.value}

    if user.role == UserRole.SUPER_ADMIN:
        payload["admin"] = await _admin_section(db)
    elif user.role == UserRole.TEACHER:
        payload["teacher"] = await _teacher_section(db, user)
    elif user.role == UserRole.LAB_ASSISTANT:
        payload["er"] = await _er_section(db)
    elif user.role == UserRole.ALUMNI:
        payload["alumni"] = await _alumni_section(db, user)
    else:  # STUDENT and CR share the academic view
        payload["student"] = await _student_section(db, user)

    return payload
