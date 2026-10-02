from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project


class ProjectService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_capstones(self):
        """Return capstone/thesis projects from the database.

        Replaces a single hardcoded "Biomimetic Underwater Autonomous Vehicle"
        entry that every caller saw regardless of what had been submitted.
        """
        rows = (
            await self.db.execute(select(Project).order_by(Project.created_at.desc()))
        ).scalars().all()

        return [
            {
                "id": str(project.id),
                "title": project.title,
                "tier": project.tier,
                "abstract": project.abstract,
                "github_repo_url": project.github_repo_url,
                "supervisor_id": str(project.supervisor_id) if project.supervisor_id else None,
            }
            for project in rows
        ]
