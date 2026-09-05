from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.facility import RoomReservation
from app.repositories.base import BaseRepository

class BookingRepository(BaseRepository[RoomReservation]):
    def __init__(self, db: AsyncSession):
        super().__init__(RoomReservation, db)

    async def get_user_reservations(self, user_id) -> list[RoomReservation]:
        stmt = select(RoomReservation).where(RoomReservation.reserved_by == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
