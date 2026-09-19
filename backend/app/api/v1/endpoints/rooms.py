import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.booking_service import BookingService
from app.schemas.booking import BookingCreate, ReservationDecisionRequest, ReservationCancelRequest
from app.api.dependencies import get_current_user, RequireRole
from app.models.user import User, UserRole

router = APIRouter(prefix="/rooms", tags=["Rooms"])

STAFF_ROLES = [UserRole.SUPER_ADMIN, UserRole.TEACHER, UserRole.LAB_ASSISTANT]


@router.get("")
async def list_rooms(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return await BookingService(db).list_rooms()


@router.post("/reservations")
async def create_booking(
    payload: BookingCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    reservation = await BookingService(db).request_booking(user.id, payload)
    return {"id": reservation.id, "status": reservation.status, "message": "Booking request submitted."}


@router.get("/reservations")
async def my_reservations(
    status: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = BookingService(db)
    reservations = await service.list_user_reservations(user.id, status)
    return await service.repo.hydrate_reservations(reservations)


@router.get("/reservations/all")
async def all_reservations(
    status: str | None = None,
    user: User = Depends(RequireRole(STAFF_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    service = BookingService(db)
    reservations = await service.list_all_reservations(status)
    return await service.repo.hydrate_reservations(reservations)


@router.post("/reservations/{reservation_id}/decide")
async def decide_reservation(
    reservation_id: uuid.UUID,
    payload: ReservationDecisionRequest,
    user: User = Depends(RequireRole(STAFF_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    reservation = await BookingService(db).decide_reservation(
        reservation_id, user.id, payload.decision, payload.reason
    )
    return {"id": reservation.id, "status": reservation.status, "message": f"Reservation {payload.decision}d."}


@router.post("/reservations/{reservation_id}/cancel")
async def cancel_reservation(
    reservation_id: uuid.UUID,
    payload: ReservationCancelRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = BookingService(db)
    reservation = await service.get_reservation(reservation_id)
    if user.role not in STAFF_ROLES and reservation.reserved_by != user.id:
        from app.core.exceptions import ForbiddenException
        raise ForbiddenException("Only the requester or staff can cancel this reservation.")
    reservation = await service.cancel_reservation(reservation_id, user.id, payload.reason)
    return {"id": reservation.id, "status": reservation.status, "message": "Reservation cancelled."}