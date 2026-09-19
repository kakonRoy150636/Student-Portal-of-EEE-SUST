import uuid
from datetime import datetime
from pydantic import BaseModel, Field, model_validator


class BookingCreate(BaseModel):
    room_id: int
    purpose: str = Field(..., min_length=3, max_length=255)
    start_time: datetime
    end_time: datetime

    @model_validator(mode="after")
    def validate_range(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        duration = (self.end_time - self.start_time).total_seconds() / 3600
        if duration > 8:
            raise ValueError("Bookings cannot exceed 8 hours")
        if duration < 15 / 60:
            raise ValueError("Bookings must be at least 15 minutes")
        return self


class ReservationResponse(BaseModel):
    id: uuid.UUID
    room_id: int
    room_number: str
    purpose: str
    start_time: datetime
    end_time: datetime
    status: str
    approved_by: uuid.UUID | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None
    cancelled_by: uuid.UUID | None = None
    cancellation_reason: str | None = None
    cancellation_at: datetime | None = None


class ReservationDecisionRequest(BaseModel):
    decision: str = Field(..., pattern="^(approve|reject)$")
    reason: str | None = Field(None, max_length=255)


class ReservationCancelRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=255)