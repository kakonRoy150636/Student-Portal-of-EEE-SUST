from sqlalchemy.ext.asyncio import AsyncSession

class ScheduleService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_my_routine(self, user_id):
        # Sample routine aligned with SUST EEE 3-1 syllabus
        return [
            {
                "id": "1",
                "course_code": "EEE 311",
                "course_title": "Electrical Machines II",
                "day_of_week": "Sunday",
                "start_time": "09:00 AM",
                "end_time": "10:30 AM",
                "room_number": "Room 304, IICT",
                "instructor_name": "Dr. Md. Tasfiq Rahman",
                "is_lab": False
            }
        ]
