from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.booking_repository import BookingRepository
from app.schemas.booking import BookingCreate
from app.models.facility import RoomReservation

class BookingService:
    def __init__(self, db: AsyncSession):
        self.repo = BookingRepository(db)

    async def request_booking(self, user_id, dto: BookingCreate):
        reservation = RoomReservation(
            room_id=dto.room_id,
            reserved_by=user_id,
            purpose=dto.purpose,
            start_time=dto.start_time,
            end_time=dto.end_time,
            status="pending"
        )
        return await self.repo.create(reservation)
