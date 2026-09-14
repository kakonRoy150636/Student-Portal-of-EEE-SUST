from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User, UserRole
from app.repositories.base import BaseRepository

class UserRepository(BaseRepository[User]):
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_identifier(self, identifier: str) -> User | None:
        stmt = select(User).where((User.identifier == identifier) | (User.email == identifier))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_pending_approval(self) -> list[User]:
        stmt = select(User).where(
            User.is_active.is_(False),
            User.role.in_([UserRole.TEACHER, UserRole.CR]),
        )
        return list((await self.db.execute(stmt)).scalars().all())
