import uuid
from datetime import datetime
from pydantic import BaseModel

class BookingCreate(BaseModel):
    room_id: int
    purpose: str
    start_time: datetime
    end_time: datetime

class ReservationResponse(BaseModel):
    id: uuid.UUID
    room_id: int
    room_number: str
    purpose: str
    start_time: datetime
    end_time: datetime
    status: str
    approved_by: uuid.UUID | None
    cancellation_reason: str | None
    cancellation_at: datetime | None
