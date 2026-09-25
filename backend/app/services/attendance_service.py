from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.models.attendance import AttendanceSession, AttendanceRecord
from app.models.academic import CourseEnrollment
from app.models.user import User
from app.repositories.attendance_repository import AttendanceRepository
from sqlalchemy import select

THRESHOLD_PERCENT = 75.0

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
            .join(AttendanceRecord, AttendanceRecord.session_id == AttendanceSession.id)
            .where(CourseEnrollment.student_id == student_id)
        )
        rows = (await self.db.execute(stmt)).all()

        per_course = {}
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
            .where(CourseEnrollment.course_offering_id == course_offering_id)
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
                "below_threshold": pct < THRESHOLD_PERCENT,
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
        session = await self.repo.get_by_id(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found.")
        if datetime.now(timezone.utc) > session.editable_until:
            raise HTTPException(status_code=400, detail="Correction window has expired.")

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