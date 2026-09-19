import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.facility import Room, RoomReservation
from app.repositories.base import BaseRepository


class BookingRepository(BaseRepository[RoomReservation]):
    def __init__(self, db: AsyncSession):
        super().__init__(RoomReservation, db)

    async def list_rooms(self) -> list[Room]:
        result = await self.db.execute(select(Room).order_by(Room.room_number))
        return list(result.scalars().all())

    async def get_user_reservations(self, user_id: uuid.UUID, status: str | None = None) -> list[RoomReservation]:
        stmt = select(RoomReservation).where(RoomReservation.reserved_by == user_id)
        if status:
            stmt = stmt.where(RoomReservation.status == status)
        stmt = stmt.order_by(RoomReservation.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_all_reservations(self, status: str | None = None) -> list[RoomReservation]:
        stmt = select(RoomReservation)
        if status:
            stmt = stmt.where(RoomReservation.status == status)
        stmt = stmt.order_by(RoomReservation.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def hydrate_reservations(self, reservations: list[RoomReservation]) -> list[dict]:
        """Serialize reservations with their room_number and human-readable bounds."""
        if not reservations:
            return []
        room_ids = {r.room_id for r in reservations}
        rooms = {
            room.id: room
            for room in (await self.db.execute(select(Room).where(Room.id.in_(room_ids)))).scalars()
        }
        out = []
        for r in reservations:
            room = rooms.get(r.room_id)
            try:
                start, end = r.slot_range.lower, r.slot_range.upper
            except (AttributeError, TypeError):
                start = end = None
            out.append({
                "id": r.id,
                "room_id": r.room_id,
                "room_number": room.room_number if room else None,
                "purpose": r.purpose,
                "start_time": start,
                "end_time": end,
                "status": r.status,
                "approved_by": r.approved_by,
                "approved_at": r.approved_at,
                "rejection_reason": r.rejection_reason,
                "cancelled_by": r.cancelled_by,
                "cancellation_reason": r.cancellation_reason,
                "cancellation_at": r.cancellation_at,
            })
        return out