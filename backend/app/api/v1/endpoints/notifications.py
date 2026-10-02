from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.notification import DeviceRegisterRequest, NotificationResponse
from app.api.dependencies import get_current_user
from app.models.user import User
from app.api.pagination import page
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.post("/devices/register")
async def register_device(
    payload: DeviceRegisterRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NotificationService(db)
    device = await service.register_device(user.id, payload.fcm_token, payload.platform)
    return {"status": "registered", "device_id": str(device.id)}


@router.get("", response_model=list[NotificationResponse])
async def list_my_notifications(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0, le=100_000),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NotificationService(db)
    return page(await service.list_for_user(user.id), limit, offset)