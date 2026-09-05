from sqlalchemy.ext.asyncio import AsyncSession

class AttendanceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_student_summary(self, student_id):
        return {"total_classes": 48, "attended": 42, "percentage": 87.5}
