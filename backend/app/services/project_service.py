from sqlalchemy.ext.asyncio import AsyncSession

class ProjectService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_capstones(self):
        return [
            {"title": "Biomimetic Underwater Autonomous Vehicle", "tier": "capstone_thesis"}
        ]
