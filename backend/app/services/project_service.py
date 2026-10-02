from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectResponse


class ProjectService:
    """Capstone/thesis projects, read from `projects`.

    Replaces a hardcoded single-row list. The supervisor name and member count
    come from the same query so a card costs one round trip.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ProjectRepository(db)

    async def list_capstones(self, limit: int = 50) -> list[ProjectResponse]:
        rows = await self.repo.list_projects(limit=limit)
        return [
            ProjectResponse(
                id=project_id,
                title=title,
                abstract=abstract,
                tier=tier,
                supervisor_name=supervisor_name,
                github_repo_url=github_repo_url,
                member_count=int(member_count or 0),
            )
            for project_id, title, abstract, tier, github_repo_url, supervisor_name, member_count in rows
        ]
