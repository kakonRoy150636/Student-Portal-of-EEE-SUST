from sqlalchemy import Row, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, ProjectMember
from app.models.user import User


class ProjectRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_projects(self, limit: int = 50) -> list[Row]:
        """Projects with their supervisor's name and member count.

        Grouped by project so the member count is one aggregate rather than a
        query per card; the supervisor join is outer because a project may be
        listed before a supervisor is assigned.
        """
        stmt = (
            select(
                Project.id,
                Project.title,
                Project.abstract,
                Project.tier,
                Project.github_repo_url,
                User.full_name.label("supervisor_name"),
                func.count(ProjectMember.student_id).label("member_count"),
            )
            .join(User, User.id == Project.supervisor_id, isouter=True)
            .join(ProjectMember, ProjectMember.project_id == Project.id, isouter=True)
            .group_by(
                Project.id, Project.title, Project.abstract, Project.tier,
                Project.github_repo_url, User.full_name,
            )
            .order_by(Project.created_at.desc())
            .limit(limit)
        )
        return list((await self.db.execute(stmt)).all())
