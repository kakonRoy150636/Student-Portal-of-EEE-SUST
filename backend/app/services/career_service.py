from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.career_repository import CareerRepository
from app.schemas.career import CareerOpportunityResponse


class CareerService:
    """Career circulars, read from `career_opportunities`.

    The table, the schema and the Alembic revision all existed while the
    endpoint returned one hardcoded internship for every caller. It now
    returns verified, unexpired rows, soonest deadline first.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CareerRepository(db)

    async def list_active_circulars(self) -> list[CareerOpportunityResponse]:
        rows = await self.repo.list_active()
        return [CareerOpportunityResponse.model_validate(row) for row in rows]
