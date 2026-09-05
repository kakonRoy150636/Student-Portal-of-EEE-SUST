from typing import Generic, TypeVar, Type, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

T = TypeVar("T")

class BaseRepository(Generic[T]):
    def __init__(self, model: Type[T], db: AsyncSession):
        self.model = model
        self.db = db

    async def get_by_id(self, id) -> Optional[T]:
        return await self.db.get(self.model, id)

    async def get_all(self, limit: int = 100) -> List[T]:
        result = await self.db.execute(select(self.model).limit(limit))
        return list(result.scalars().all())

    async def create(self, entity: T) -> T:
        self.db.add(entity)
        await self.db.flush()
        return entity
