from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.academic import ClassSchedule
from app.repositories.base import BaseRepository

class ScheduleRepository(BaseRepository[ClassSchedule]):
    def __init__(self, db: AsyncSession):
        super().__init__(ClassSchedule, db)

    async def get_schedules_by_offering(self, offering_id) -> list[ClassSchedule]:
        stmt = select(ClassSchedule).where(ClassSchedule.course_offering_id == offering_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
