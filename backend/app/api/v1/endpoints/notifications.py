import asyncio
import json
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db, AsyncSessionLocal
from app.models.notification import Notification, DeviceToken
from app.schemas.notification import (
    DeviceRegisterRequest, NotificationResponse, NotificationPreferencesRequest,
    NotificationPreferencesResponse,
)
from app.api.dependencies import get_current_user
from app.models.user import User
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


async def notification_snapshot(db, user_id):
    items = await NotificationService(db).list_for_user(user_id)
    count = await db.scalar(select(func.count()).select_from(Notification).where(
        Notification.recipient_id == user_id, Notification.is_read.is_(False)))
    return {"items": [NotificationResponse.model_validate(item).model_dump(mode="json") for item in items],
            "unread_count": count or 0}


async def notification_events(request, user_id, sessions):
    """Short-lived authenticated SSE; no token is placed in a URL.

    Each poll releases its database connection. Reconnect after 45s rechecks
    the caller's current credentials; no long-lived subscription outlives auth.
    """
    deadline = time.monotonic() + 45
    previous = None
    while time.monotonic() < deadline and not await request.is_disconnected():
        async with sessions() as db:
            active = await db.scalar(select(User.is_active).where(User.id == user_id))
            if not active:
                break
            payload = json.dumps(await notification_snapshot(db, user_id))
        if payload != previous:
            yield f"event: notifications\ndata: {payload}\n\n"
            previous = payload
        else:
            yield ": heartbeat\n\n"
        await asyncio.sleep(3)


@router.get("/summary")
async def summary(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await notification_snapshot(db, user.id)


@router.get("/stream")
async def stream(request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user_id = user.id
    await db.close()  # do not retain the auth query's connection during SSE
    return StreamingResponse(notification_events(request, user_id, AsyncSessionLocal),
                             media_type="text/event-stream", headers={
                                 "Cache-Control": "no-store", "X-Accel-Buffering": "no"})


@router.patch("/read-all")
async def read_all(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await db.execute(update(Notification).where(Notification.recipient_id == user.id).values(is_read=True))
    await db.commit()
    return {"status": "read"}


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def read_one(notification_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    item = await db.scalar(select(Notification).where(Notification.id == notification_id, Notification.recipient_id == user.id))
    if item is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    item.is_read = True
    await db.commit()
    return item


@router.delete("/devices/{device_id}", status_code=204)
async def unregister_device(device_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await db.execute(delete(DeviceToken).where(DeviceToken.id == device_id, DeviceToken.user_id == user.id))
    await db.commit()


@router.get("/preferences", response_model=NotificationPreferencesResponse)
async def get_preferences(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await NotificationService(db).get_preferences(user.id)


@router.put("/preferences", response_model=NotificationPreferencesResponse)
async def update_preferences(payload: NotificationPreferencesRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await NotificationService(db).set_preferences(user.id, payload)


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
