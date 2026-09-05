from sqlalchemy.ext.asyncio import AsyncSession
from app.integrations.firebase_client import dispatch_push_notification

class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def send_10m_alert(self, fcm_token: str, course_code: str, room: str):
        return dispatch_push_notification(
            token=fcm_token,
            title=f"Class Alert: {course_code}",
            body=f"Your lecture starts in 10 minutes at {room}."
        )
