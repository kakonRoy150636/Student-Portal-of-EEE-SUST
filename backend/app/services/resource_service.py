from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.resource_repository import ResourceRepository

class ResourceService:
    def __init__(self, db: AsyncSession):
        self.repo = ResourceRepository(db)

    async def search_resources(self, q: str | None = None):
        return await self.repo.search(q)
