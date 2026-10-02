from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.career import CareerOpportunity


class CareerRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_active(self, limit: int = 50) -> list[CareerOpportunity]:
        """Verified opportunities whose deadline has not passed.

        Both filters matter: an unverified post is one nobody has checked, and
        an expired one wastes a student's time. Ordering by deadline puts the
        most urgent first, which is the only ordering a student cares about.
        """
        stmt = (
            select(CareerOpportunity)
            .where(
                CareerOpportunity.is_verified.is_(True),
                CareerOpportunity.application_deadline >= date.today(),
            )
            .order_by(CareerOpportunity.application_deadline.asc())
            .limit(limit)
        )
        return list((await self.db.execute(stmt)).scalars().all())
