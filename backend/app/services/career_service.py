from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.career import CareerOpportunity


class CareerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_active_circulars(self):
        """Return verified, still-open career opportunities from the database.

        Previously this returned a single hardcoded internship entry, so every
        student saw the same invented listing regardless of what had actually
        been posted and verified.
        """
        stmt = (
            select(CareerOpportunity)
            .where(CareerOpportunity.is_verified.is_(True))
            .order_by(CareerOpportunity.application_deadline.asc())
        )
        rows = (await self.db.execute(stmt)).scalars().all()

        return [
            {
                "id": str(item.id),
                "title": item.title,
                "organization": item.organization_name,
                "type": item.type,
                "location": item.location,
                "deadline": item.application_deadline.isoformat() if item.application_deadline else None,
                "application_target": item.application_target,
                "description": item.description,
                "tags": item.tags or [],
                "is_verified": item.is_verified,
            }
            for item in rows
        ]
