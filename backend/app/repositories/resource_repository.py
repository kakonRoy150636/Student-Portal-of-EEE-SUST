from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.resource import AcademicResource
from app.repositories.base import BaseRepository

class ResourceRepository(BaseRepository[AcademicResource]):
    def __init__(self, db: AsyncSession):
        super().__init__(AcademicResource, db)

    async def search(self, q: str | None = None) -> list[AcademicResource]:
        stmt = select(AcademicResource)
        if q:
            stmt = stmt.where(AcademicResource.title.ilike(f"%{q}%"))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
