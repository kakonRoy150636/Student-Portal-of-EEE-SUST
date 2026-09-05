from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.booking_repository import BookingRepository
from app.schemas.booking import BookingCreate

class BookingService:
    def __init__(self, db: AsyncSession):
        self.repo = BookingRepository(db)

    async def request_booking(self, user_id, dto: BookingCreate):
        return {"id": "res-new-001", "room_id": dto.room_id, "status": "pending"}
