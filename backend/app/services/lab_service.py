from sqlalchemy.ext.asyncio import AsyncSession

class LabService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_equipment(self):
        return [
            {"tag": "SUST-EEE-EL-042", "model": "Rigol DS1054Z Oscilloscope", "status": "operational"}
        ]
