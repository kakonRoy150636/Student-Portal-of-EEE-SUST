from sqlalchemy.ext.asyncio import AsyncSession

class CareerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_active_circulars(self):
        return [
            {"title": "VLSI Design Intern", "organization": "Neural Semiconductor", "deadline": "2026-10-15"}
        ]
