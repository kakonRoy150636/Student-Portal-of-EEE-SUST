from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.booking_service import BookingService
from app.schemas.booking import BookingCreate
from app.api.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/rooms", tags=["Rooms"])

@router.get("")
async def list_rooms():
    return [
        {"id": 1, "room_number": "Room 304", "capacity": 80},
        {"id": 2, "room_number": "Electronics Lab", "capacity": 40}
    ]

@router.post("/reservations")
async def create_booking(payload: BookingCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = BookingService(db)
    return await service.request_booking(user.id, payload)
