from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resource import AcademicResource
from app.repositories.base import BaseRepository


class ResourceRepository(BaseRepository[AcademicResource]):
    def __init__(self, db: AsyncSession):
        super().__init__(AcademicResource, db)

    async def search(self, escaped_query: str) -> list[AcademicResource]:
        """Title prefix/substring match.

        ``escaped_query`` is expected to have had its LIKE wildcards escaped by
        the service -- pass raw user input here and ``%`` will match everything.
        """
        stmt = (
            select(AcademicResource)
            .where(AcademicResource.title.ilike(f"%{escaped_query}%", escape="\\"))
            .order_by(AcademicResource.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_recent(self, limit: int = 50) -> list[AcademicResource]:
        stmt = (
            select(AcademicResource)
            .order_by(AcademicResource.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
