from fastapi import APIRouter, Depends
from app.schemas.notification import DeviceRegisterRequest
from app.api.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.post("/devices/register")
async def register_device(payload: DeviceRegisterRequest, user: User = Depends(get_current_user)):
    return {"status": "registered", "token": payload.fcm_token[:8] + "..."}
