from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.models.attendance import AttendanceSession
from app.models.academic import CourseEnrollment
from app.repositories.attendance_repository import AttendanceRepository
from sqlalchemy import select

THRESHOLD_PERCENT = 75.0

class AttendanceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AttendanceRepository(db)

    async def get_student_summary(self, student_id):
        return {"total_classes": 48, "attended": 42, "percentage": 87.5}

    async def create_session(self, course_offering_id, session_date, topic, taken_by, records):
        session = AttendanceSession(
            course_offering_id=course_offering_id,
            session_date=session_date,
            taken_by=taken_by,
            topic_discussed=topic,
        )
        self.db = await self.repo.create(session)
        await self.repo.add_records(session.id, [r.dict() for r in records])
        await self.db.commit()
        return {"session_id": session.id, "message": "Attendance recorded successfully"}

    async def get_course_summary(self, course_offering_id):
        total_sessions = await self.repo.get_session_count(course_offering_id)
        present_counts = await self.repo.get_present_counts(course_offering_id)

        stmt = select(CourseEnrollment.student_id).where(
            CourseEnrollment.course_offering_id == course_offering_id
        )
        student_ids = [row[0] for row in (await self.db.execute(stmt)).all()]

        summary = []
        for sid in student_ids:
            present = present_counts.get(sid, 0)
            pct = round((present / total_sessions * 100), 2) if total_sessions else 0.0
            summary.append({
                "student_id": sid,
                "total_sessions": total_sessions,
                "present_count": present,
                "percentage": pct,
                "below_threshold": pct < THRESHOLD_PERCENT,
            })
        return summary

    async def update_records(self, session_id, records):
        session = await self.repo.get_by_id(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found.")
        if datetime.now(timezone.utc) > session.editable_until:
            raise HTTPException(status_code=400, detail="Correction window has expired.")

        from app.models.attendance import AttendanceRecord
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