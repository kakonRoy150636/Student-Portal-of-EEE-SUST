from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.repositories.base import BaseRepository

class UserRepository(BaseRepository[User]):
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_identifier(self, identifier: str) -> User | None:
        stmt = select(User).where((User.identifier == identifier) | (User.email == identifier))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
