from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.models.attendance import AttendanceSession, AttendanceRecord
from app.models.academic import ACTIVE_ENROLLMENT_STATUSES, CourseEnrollment, CourseOffering, Semester
from app.models.user import User
from app.repositories.attendance_repository import AttendanceRepository
from sqlalchemy import select, and_

THRESHOLD_PERCENT = 75.0


def _is_expired(deadline: datetime) -> bool:
    """Whether an attendance correction window has closed.

    ``editable_until`` is TIMESTAMPTZ in Postgres (asyncpg returns aware
    datetimes), but SQLite -- used by the test suite -- has no timezone-aware
    storage and returns naive values. Comparing either against an aware
    ``datetime.now(timezone.utc)`` raises TypeError, which would surface as a
    500 instead of a normal "window expired" rejection, so both sides are
    normalised to naive UTC first.
    """
    now = datetime.now(timezone.utc)
    if deadline.tzinfo is None:
        return deadline < now.replace(tzinfo=None)
    return deadline < now


class AttendanceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AttendanceRepository(db)

    async def get_student_summary(self, student_id):
        """Aggregate attendance across all enrolled courses for a student."""
        stmt = (
            select(
                CourseEnrollment.course_offering_id,
                AttendanceSession.id.label("session_id"),
                AttendanceRecord.status,
            )
            .join(AttendanceSession, AttendanceSession.course_offering_id == CourseEnrollment.course_offering_id)
            .join(CourseOffering, CourseOffering.id == CourseEnrollment.course_offering_id)
            .join(Semester, Semester.id == CourseOffering.semester_id)
            .outerjoin(AttendanceRecord, and_(
                AttendanceRecord.session_id == AttendanceSession.id,
                AttendanceRecord.student_id == student_id,
            ))
            .where(
                CourseEnrollment.student_id == student_id,
                CourseEnrollment.status.in_(ACTIVE_ENROLLMENT_STATUSES),
                Semester.is_active.is_(True),
            )
        )
        rows = (await self.db.execute(stmt)).all()

        per_course: dict[UUID, dict[str, int]] = {}
        for offering_id, session_id, status in rows:
            per_course.setdefault(offering_id, {"present": 0, "total": 0})
            per_course[offering_id]["total"] += 1
            if status in ("present", "late"):
                per_course[offering_id]["present"] += 1

        total = len(rows)
        attended = sum(1 for _, _, status in rows if status in ("present", "late"))
        percentage = round(attended / total * 100, 2) if total else 0.0
        return {
            "total_classes": total,
            "attended": attended,
            "percentage": percentage,
            "below_threshold": percentage < THRESHOLD_PERCENT if total else False,
            "per_course": per_course,
        }

    async def create_session(self, course_offering_id, session_date, topic, taken_by, records):
        student_ids = [record.student_id for record in records]
        if student_ids:
            enrolled_ids = set((await self.db.scalars(
                select(CourseEnrollment.student_id).where(
                    CourseEnrollment.course_offering_id == course_offering_id,
                    CourseEnrollment.student_id.in_(student_ids),
                    CourseEnrollment.status.in_(ACTIVE_ENROLLMENT_STATUSES),
                )
            )).all())
            if enrolled_ids != set(student_ids):
                raise HTTPException(
                    status_code=422,
                    detail="Attendance records may only include active students enrolled in this course.",
                )
        session = AttendanceSession(
            course_offering_id=course_offering_id,
            session_date=session_date,
            taken_by=taken_by,
            topic_discussed=topic,
        )
        await self.repo.create(session)
        await self.repo.add_records(session.id, [r.model_dump() for r in records])
        await self.db.commit()
        return {"session_id": session.id, "message": "Attendance recorded successfully"}

    async def get_course_summary(self, course_offering_id):
        total_sessions = await self.repo.get_session_count(course_offering_id)
        present_counts = await self.repo.get_present_counts(course_offering_id)

        stmt = (
            select(CourseEnrollment.student_id, User.full_name)
            .join(User, User.id == CourseEnrollment.student_id)
            .where(
                CourseEnrollment.course_offering_id == course_offering_id,
                CourseEnrollment.status.in_(ACTIVE_ENROLLMENT_STATUSES),
            )
        )
        students = (await self.db.execute(stmt)).all()

        summary = []
        for sid, full_name in students:
            present = present_counts.get(sid, 0)
            pct = round((present / total_sessions * 100), 2) if total_sessions else 0.0
            summary.append({
                "student_id": sid,
                "full_name": full_name,
                "total_sessions": total_sessions,
                "present_count": present,
                "percentage": pct,
                "below_threshold": pct < THRESHOLD_PERCENT if total_sessions else False,
            })
        return summary

    async def get_offering_id_for_session(self, session_id):
        """Resolve the course an attendance session belongs to.

        The update route needs this to authorise the caller, but
        ``update_records`` was the only entry point exposed, so there was no
        way to check ownership. Raising 404 for an unknown session keeps a
        caller from distinguishing "no such session" from "not your course".
        """
        session = await self.repo.get_by_id(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found.")
        return session.course_offering_id

    async def update_records(self, session_id, records):
        session = await self.db.scalar(
            select(AttendanceSession)
            .where(AttendanceSession.id == session_id)
            .with_for_update()
        )
        if not session:
            raise HTTPException(status_code=404, detail="Session not found.")
        if _is_expired(session.editable_until):
            raise HTTPException(status_code=400, detail="Correction window has expired.")

        student_ids = [record.student_id for record in records]
        if student_ids:
            existing_ids = set((await self.db.scalars(
                select(AttendanceRecord.student_id).where(
                    AttendanceRecord.session_id == session_id,
                    AttendanceRecord.student_id.in_(student_ids),
                )
            )).all())
            if existing_ids != set(student_ids):
                raise HTTPException(
                    status_code=422,
                    detail="Attendance records must refer to students recorded in this session.",
                )

        for r in records:
            stmt = select(AttendanceRecord).where(
                AttendanceRecord.session_id == session_id,
                AttendanceRecord.student_id == r.student_id,
            )
            record = (await self.db.execute(stmt)).scalar_one_or_none()
            if record:
                record.status = r.status
        await self.db.commit()
        return {"message": "Attendance updated."}
