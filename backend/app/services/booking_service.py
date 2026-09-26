import uuid
from datetime import datetime, timezone
from sqlalchemy import select, func, literal
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.booking_repository import BookingRepository
from app.schemas.booking import BookingCreate
from app.models.facility import Room, RoomReservation
from app.core.exceptions import (
    NotFoundException,
    ResourceConflictException,
    ForbiddenException,
)


class BookingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BookingRepository(db)

    async def list_rooms(self) -> list[Room]:
        return await self.repo.list_rooms()

    async def request_booking(self, user_id: uuid.UUID, dto: BookingCreate) -> RoomReservation:
        room = await self.db.get(Room, dto.room_id)
        if not room:
            raise NotFoundException("Room not found.")

        # Pre-flight check (friendly 409 before hitting the DB constraint).
        cursor = await self.db.execute(
            select(func.count(RoomReservation.id)).where(
                RoomReservation.room_id == dto.room_id,
                RoomReservation.status.in_(["pending", "approved"]),
                RoomReservation.slot_range.op("&&")(func.tstzrange(dto.start_time, dto.end_time)),
            )
        )
        overlaps = cursor.scalar_one()
        if overlaps:
            raise ResourceConflictException("This room is already reserved for the requested slot.")

        reservation = RoomReservation(
            room_id=dto.room_id,
            reserved_by=user_id,
            purpose=dto.purpose,
            slot_range=func.tstzrange(dto.start_time, dto.end_time),
            status="pending",
        )
        try:
            return await self.repo.create(reservation)
        except IntegrityError:
            # The GiST exclusion constraint rejects the overlap under
            # concurrency. Only IntegrityError means "slot taken" — a broad
            # except here would report genuine DB faults as booking conflicts.
            # The caller's session handles the rollback, so the failed flush
            # must not be swallowed mid-transaction.
            raise ResourceConflictException("This room is already reserved for the requested slot.")

    async def get_reservation(self, reservation_id: uuid.UUID) -> RoomReservation:
        reservation = await self.repo.get_by_id(reservation_id)
        if not reservation:
            raise NotFoundException("Reservation not found.")
        return reservation

    async def list_user_reservations(self, user_id: uuid.UUID, status: str | None = None) -> list[RoomReservation]:
        return await self.repo.get_user_reservations(user_id, status=status)

    async def list_all_reservations(self, status: str | None = None) -> list[RoomReservation]:
        return await self.repo.get_all_reservations(status=status)

    async def decide_reservation(
        self,
        reservation_id: uuid.UUID,
        actor_id: uuid.UUID,
        decision: str,
        reason: str | None = None,
    ) -> RoomReservation:
        """Teacher/admin approval or rejection of a pending reservation."""
        reservation = await self.get_reservation(reservation_id)
        if reservation.status != "pending":
            raise ResourceConflictException("Only pending reservations can be decided.")

        if decision == "approve":
            reservation.status = "approved"
            reservation.approved_by = actor_id
            reservation.approved_at = datetime.now(timezone.utc)
            reservation.rejection_reason = None
        else:
            reservation.status = "rejected"
            reservation.rejection_reason = reason or "Rejected by the department."
            reservation.approved_by = None
            reservation.approved_at = None

        await self.db.commit()
        return reservation

    async def cancel_reservation(
        self,
        reservation_id: uuid.UUID,
        actor_id: uuid.UUID,
        reason: str,
    ) -> RoomReservation:
        reservation = await self.get_reservation(reservation_id)
        if reservation.status in ("cancelled", "rejected"):
            raise ResourceConflictException("This reservation can no longer be cancelled.")

        reservation.status = "cancelled"
        reservation.cancelled_by = actor_id
        reservation.cancellation_reason = reason
        reservation.cancellation_at = datetime.now(timezone.utc)
        await self.db.commit()
        return reservation

    async def ensure_can_manage(self, reservation: RoomReservation, actor_id: uuid.UUID) -> None:
        """Owner or staff can cancel; only staff can approve/reject (enforced at route too)."""
        if reservation.reserved_by != actor_id:
            raise ForbiddenException("You are not allowed to modify this reservation.")