from sqlalchemy import Row, func, literal_column, or_, select
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic import Course
from app.models.resource import AcademicResource
from app.models.user import User
from app.repositories.base import BaseRepository

# Matches the language configuration the generated column was built with
# (schema.sql: to_tsvector('english', title || ' ' || description)). Using a
# different configuration would compile a query that cannot use the GIN index.
_TS_CONFIG = "english"


def _escape_like(value: str) -> str:
    """Escape LIKE metacharacters so a search term is matched literally.

    Without this, ``q=%`` turns a lookup into a full table scan and ``_``
    matches any character -- user input silently becoming pattern syntax.
    """
    return value.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")


class ResourceRepository(BaseRepository[AcademicResource]):
    """Reads are projections: resource + course code + uploader name.

    Both extras are display fields, so they are joined here rather than
    lazily fetched per row in the service (which would be two extra queries
    per result).
    """

    def __init__(self, db: AsyncSession):
        super().__init__(AcademicResource, db)

    def _select(self):
        return (
            select(
                AcademicResource,
                Course.course_code,
                User.full_name.label("uploader_name"),
            )
            .join(Course, Course.id == AcademicResource.course_id, isouter=True)
            .join(User, User.id == AcademicResource.uploader_id, isouter=True)
        )

    def _base(self, category: str | None):
        stmt = self._select().where(AcademicResource.status == "ready")
        if category:
            stmt = stmt.where(AcademicResource.category == category)
        return stmt

    async def search(
        self,
        q: str | None = None,
        category: str | None = None,
        limit: int = 50,
    ) -> list[Row]:
        if q:
            # Postgres full-text search first: the tsv_search column is
            # generated over title *and* description and has a GIN index, so
            # this is both faster and more useful than a substring scan.
            try:
                # `literal_column` rather than a mapped attribute: the column
                # is GENERATED ALWAYS, so mapping it would make SQLAlchemy try
                # to write NULL into it on INSERT ("cannot insert a non-DEFAULT
                # value into column").
                tsv = literal_column("academic_resources.tsv_search")
                stmt = self._base(category).where(
                    tsv.op("@@")(func.plainto_tsquery(_TS_CONFIG, q))
                )
                async with self.db.begin_nested():
                    return list((await self.db.execute(stmt.limit(limit))).all())
            except (ProgrammingError, OperationalError):
                # SQLite has no tsvector; fall through to the ILIKE path. The
                # failed statement is contained by a savepoint (see the
                # begin_nested above), so the session stays usable -- a plain
                # rollback here would expire every ORM object the caller holds.
                pass

        return await self.search_fallback(q=q, category=category, limit=limit)

    async def search_fallback(
        self,
        q: str | None = None,
        category: str | None = None,
        limit: int = 50,
    ) -> list[Row]:
        stmt = self._base(category)
        if q:
            like = f"%{_escape_like(q)}%"
            stmt = stmt.where(
                or_(
                    AcademicResource.title.ilike(like, escape="\\"),
                    AcademicResource.description.ilike(like, escape="\\"),
                )
            )
        stmt = stmt.order_by(AcademicResource.created_at.desc()).limit(limit)
        return list((await self.db.execute(stmt)).all())

    async def get_projection(self, resource_id) -> Row | None:
        stmt = self._select().where(AcademicResource.id == resource_id)
        return (await self.db.execute(stmt)).first()
