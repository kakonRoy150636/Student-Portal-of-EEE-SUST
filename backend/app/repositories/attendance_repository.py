from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.attendance import AttendanceSession, AttendanceRecord
from app.repositories.base import BaseRepository

class AttendanceRepository(BaseRepository[AttendanceSession]):
    def __init__(self, db: AsyncSession):
        super().__init__(AttendanceSession, db)

    async def add_records(self, session_id, records: list[dict]):
        for r in records:
            self.db.add(AttendanceRecord(session_id=session_id, student_id=r["student_id"], status=r["status"]))
        await self.db.flush()

    async def get_session_count(self, course_offering_id) -> int:
        stmt = select(func.count(AttendanceSession.id)).where(
            AttendanceSession.course_offering_id == course_offering_id
        )
        return (await self.db.execute(stmt)).scalar_one()

    async def get_present_counts(self, course_offering_id) -> dict:
        stmt = (
            select(AttendanceRecord.student_id, func.count(AttendanceRecord.id))
            .join(AttendanceSession, AttendanceSession.id == AttendanceRecord.session_id)
            .where(
                AttendanceSession.course_offering_id == course_offering_id,
                AttendanceRecord.status.in_(["present", "late"]),
            )
            .group_by(AttendanceRecord.student_id)
        )
        return dict((await self.db.execute(stmt)).all())