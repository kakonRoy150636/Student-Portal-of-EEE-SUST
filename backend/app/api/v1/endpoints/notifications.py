from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.notification import DeviceRegisterRequest, NotificationResponse
from app.api.dependencies import get_current_user
from app.models.user import User
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
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NotificationService(db)
    return await service.list_for_user(user.id)