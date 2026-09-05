import uuid
from pydantic import BaseModel

class DeviceRegisterRequest(BaseModel):
    fcm_token: str
    platform: str = "web"

class NotificationResponse(BaseModel):
    id: int
    title: str
    body: str
    is_read: bool
