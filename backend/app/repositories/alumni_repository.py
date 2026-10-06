"""Persistence helpers for the Alumni Portal."""
from __future__ import annotations

import uuid

from sqlalchemy import Select, ColumnElement, and_, func, literal_column, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.alumni import (
    AlumniProfile,
    AlumniEmployment,
    Event,
    EventRSVP,
    GalleryAlbum,
    GalleryPhoto,
    MentorshipPair,
    NewsPost,
    Scholarship,
    ScholarshipApplication,
)
from app.models.user import User
from app.repositories.base import BaseRepository

# Postgres text-search configuration for the alumni directory. This single
# constant is the authority: the generated column (schema.sql / migration 005)
# and the query below must both use it, or the two sides stem differently and
# matches silently disappear. ``test_alumni_directory_fts.py`` enforces that
# the repository and the DDL agree.
DIRECTORY_TS_CONFIG = "english"


def _directory_tsvector():
    """The stored ``alumni_profiles.search_tsv`` generated column.

    It is built by ``to_tsvector('english', ...)`` in ``database/schema.sql``
    and ``database/migrations/005_alumni_search_and_career.sql``, and indexed
    by the GIN index ``ix_alumni_profiles_search``. Referencing the column
    rather than recomputing the expression is what lets Postgres match
    against that index at all -- an expression has to match the indexed
    expression structurally, and a mismatched configuration would not.

    ``plainto_tsquery`` must therefore be called with the same ``'english'``
    configuration (see :data:`DIRECTORY_TS_CONFIG`). Mixing the two silently
    returns no matches: a token stemmed by one config does not compare equal
    to the same token produced by another, so
    ``to_tsvector('english', 'power systems engineering') @@
    plainto_tsquery('simple', 'engineering')`` is false while the
    ``'english'``/``'english'`` pair is true.
    """
    return literal_column("alumni_profiles.search_tsv")


def _directory_tsquery(q: str):
    return func.plainto_tsquery(DIRECTORY_TS_CONFIG, q)


class AlumniRepository(BaseRepository[AlumniProfile]):
    def __init__(self, db: AsyncSession):
        super().__init__(AlumniProfile, db)

    async def get_profile_by_user_id(self, user_id: uuid.UUID) -> AlumniProfile | None:
        stmt = (
            select(AlumniProfile)
            .options(selectinload(AlumniProfile.user))
            .where(AlumniProfile.user_id == user_id)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_profile(self, profile_id: uuid.UUID) -> AlumniProfile | None:
        stmt = (
            select(AlumniProfile)
            .options(selectinload(AlumniProfile.user))
            .where(AlumniProfile.id == profile_id)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_pending_verifications(self) -> list[AlumniProfile]:
        stmt = (
            select(AlumniProfile)
            .options(selectinload(AlumniProfile.user))
            .where(AlumniProfile.membership_status == "pending")
            .order_by(AlumniProfile.created_at.asc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def search_directory(
        self,
        q: str | None = None,
        batch_year: int | None = None,
        industry: str | None = None,
        visible_only: bool = True,
        membership_status: str | None = "active",
        limit: int = 50,
    ) -> list[AlumniProfile]:
        stmt: Select = select(AlumniProfile).options(selectinload(AlumniProfile.user))
        filters: list[ColumnElement[bool]] = []
        if visible_only:
            filters.append(AlumniProfile.is_visible.is_(True))
        if membership_status:
            filters.append(AlumniProfile.membership_status == membership_status)
        if batch_year is not None:
            filters.append(AlumniProfile.batch_year == batch_year)
        if industry:
            filters.append(AlumniProfile.industry.ilike(industry))
        if q:
            # Matched against the stored search_tsv column, so the GIN index
            # ix_alumni_profiles_search applies and the query config matches the
            # one the generated column was built with. On SQLite (unit tests)
            # the @@ operator is unavailable, so the service falls back to
            # search_directory_fallback() (ILIKE) when this raises.
            filters.append(_directory_tsvector().op("@@")(_directory_tsquery(q)))
        if filters:
            stmt = stmt.where(and_(*filters))
        stmt = stmt.order_by(AlumniProfile.batch_year.desc(), AlumniProfile.created_at.desc()).limit(limit)
        return list((await self.db.execute(stmt)).scalars().all())

    async def search_directory_fallback(
        self,
        q: str | None = None,
        batch_year: int | None = None,
        industry: str | None = None,
        visible_only: bool = True,
        membership_status: str | None = "active",
        limit: int = 50,
    ) -> list[AlumniProfile]:
        """ILIKE fallback used by the SQLite test suite (no tsvector)."""
        stmt: Select = select(AlumniProfile).options(selectinload(AlumniProfile.user))
        filters: list[ColumnElement[bool]] = []
        if visible_only:
            filters.append(AlumniProfile.is_visible.is_(True))
        if membership_status:
            filters.append(AlumniProfile.membership_status == membership_status)
        if batch_year is not None:
            filters.append(AlumniProfile.batch_year == batch_year)
        if industry:
            filters.append(AlumniProfile.industry.ilike(industry))
        if q:
            like = f"%{q}%"
            filters.append(
                or_(
                    AlumniProfile.department.ilike(like),
                    AlumniProfile.current_company.ilike(like),
                    AlumniProfile.industry.ilike(like),
                    AlumniProfile.designation.ilike(like),
                    func.cast(AlumniProfile.batch_year, AlumniProfile.department.type).ilike(like),
                )
            )
        if filters:
            stmt = stmt.where(and_(*filters))
        stmt = stmt.order_by(AlumniProfile.batch_year.desc(), AlumniProfile.created_at.desc()).limit(limit)
        return list((await self.db.execute(stmt)).scalars().all())

    async def batch_counts(self) -> dict[int, int]:
        rows = (await self.db.execute(
            select(AlumniProfile.batch_year, func.count(AlumniProfile.id))
            .where(AlumniProfile.membership_status == "active", AlumniProfile.is_visible.is_(True))
            .group_by(AlumniProfile.batch_year)
        )).all()
        return {int(year): int(count) for year, count in rows}

    def _directory_filters(self, *, batch: int | None, company: str | None, country: str | None,
                           sector: str | None, q: str | None):
        filters: list[ColumnElement[bool]] = [
            AlumniProfile.membership_status == "active",
            AlumniProfile.is_visible.is_(True),
        ]
        if batch is not None:
            filters.append(AlumniProfile.batch_year == batch)
        if company:
            like = f"%{company}%"
            filters.append(or_(
                AlumniEmployment.organization.ilike(like),
                AlumniProfile.current_company.ilike(like),
            ))
        if country:
            like = f"%{country}%"
            filters.append(or_(
                AlumniEmployment.country.ilike(like),
                AlumniProfile.current_country.ilike(like),
            ))
        if sector:
            filters.append(AlumniEmployment.sector == sector)
        if q:
            like = f"%{q}%"
            filters.append(or_(
                User.full_name.ilike(like),
                AlumniProfile.department.ilike(like),
                AlumniProfile.current_company.ilike(like),
                AlumniProfile.industry.ilike(like),
                AlumniEmployment.organization.ilike(like),
                AlumniEmployment.position.ilike(like),
            ))
        return filters

    def _directory_from(self):
        return (
            AlumniProfile.__table__
            .join(User.__table__, User.id == AlumniProfile.user_id)
            .outerjoin(
                AlumniEmployment.__table__,
                and_(
                    AlumniEmployment.alumni_id == AlumniProfile.id,
                    AlumniEmployment.is_current.is_(True),
                ),
            )
        )

    async def directory_page(self, *, batch: int | None, company: str | None, country: str | None,
                             sector: str | None, q: str | None, page: int, page_size: int):
        filters = self._directory_filters(batch=batch, company=company, country=country, sector=sector, q=q)
        total = int((await self.db.scalar(
            select(func.count(func.distinct(AlumniProfile.id)))
            .select_from(self._directory_from())
            .where(and_(*filters))
        )) or 0)
        rows = (await self.db.execute(
            select(AlumniProfile, User, AlumniEmployment)
            .select_from(self._directory_from())
            .where(and_(*filters))
            .order_by(AlumniProfile.batch_year.desc(), User.full_name.asc(), AlumniProfile.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )).all()
        return rows, total

    async def detail(self, profile_id: uuid.UUID) -> AlumniProfile | None:
        stmt = (
            select(AlumniProfile)
            .options(selectinload(AlumniProfile.user), selectinload(AlumniProfile.employments))
            .where(
                AlumniProfile.id == profile_id,
                AlumniProfile.membership_status == "active",
                AlumniProfile.is_visible.is_(True),
            )
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def summary(self, year: int) -> dict:
        base = select(AlumniProfile.id).where(
            AlumniProfile.batch_year == year,
            AlumniProfile.membership_status == "active",
            AlumniProfile.is_visible.is_(True),
        )
        total = int((await self.db.scalar(select(func.count()).select_from(base.subquery()))) or 0)
        current = AlumniEmployment.__table__.join(AlumniProfile.__table__, AlumniProfile.id == AlumniEmployment.alumni_id)
        current_where = and_(
            AlumniProfile.batch_year == year,
            AlumniProfile.membership_status == "active",
            AlumniProfile.is_visible.is_(True),
            AlumniEmployment.is_current.is_(True),
        )
        employed = int((await self.db.scalar(
            select(func.count(func.distinct(AlumniEmployment.alumni_id))).select_from(current).where(
                current_where, AlumniEmployment.sector != "higher_study",
                AlumniEmployment.organization.is_not(None),
            )
        )) or 0)
        higher_study = int((await self.db.scalar(
            select(func.count(func.distinct(AlumniEmployment.alumni_id))).select_from(current).where(
                current_where, AlumniEmployment.sector == "higher_study",
            )
        )) or 0)
        abroad = int((await self.db.scalar(
            select(func.count(func.distinct(AlumniEmployment.alumni_id))).select_from(current).where(
                current_where,
                AlumniEmployment.country.is_not(None),
                func.lower(AlumniEmployment.country) != "bangladesh",
            )
        )) or 0)
        company_rows = (await self.db.execute(
            select(AlumniEmployment.organization, func.count(func.distinct(AlumniEmployment.alumni_id)).label("count"))
            .select_from(current).where(current_where)
            .group_by(AlumniEmployment.organization).order_by(func.count().desc(), AlumniEmployment.organization.asc()).limit(5)
        )).all()
        country_rows = (await self.db.execute(
            select(AlumniEmployment.country, func.count(func.distinct(AlumniEmployment.alumni_id)).label("count"))
            .select_from(current).where(current_where, AlumniEmployment.country.is_not(None))
            .group_by(AlumniEmployment.country).order_by(func.count().desc(), AlumniEmployment.country.asc()).limit(5)
        )).all()
        return {
            "year": year,
            "total": total,
            "employed": employed,
            "higher_study": higher_study,
            "abroad": abroad,
            "top_companies": [{"name": str(name), "count": int(count)} for name, count in company_rows],
            "top_countries": [{"name": str(name), "count": int(count)} for name, count in country_rows],
        }


class EventRepository(BaseRepository[Event]):
    def __init__(self, db: AsyncSession):
        super().__init__(Event, db)

    async def list_events(self, published_only: bool = True, upcoming_only: bool = False) -> list[Event]:
        stmt = select(Event)
        if published_only:
            stmt = stmt.where(Event.is_published.is_(True))
        if upcoming_only:
            stmt = stmt.where(Event.starts_at >= func.now())
        stmt = stmt.order_by(Event.starts_at.asc())
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_event(self, event_id: uuid.UUID) -> Event | None:
        stmt = select(Event).options(selectinload(Event.rsvps)).where(Event.id == event_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def attending_count(self, event_id: uuid.UUID) -> int:
        stmt = select(func.count(EventRSVP.id)).where(
            EventRSVP.event_id == event_id,
            EventRSVP.rsvp_status == "attending",
        )
        return int((await self.db.execute(stmt)).scalar_one() or 0)

    async def get_rsvp(self, event_id: uuid.UUID, user_id: uuid.UUID) -> EventRSVP | None:
        stmt = select(EventRSVP).where(EventRSVP.event_id == event_id, EventRSVP.user_id == user_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_user_rsvps(self, user_id: uuid.UUID) -> list[EventRSVP]:
        stmt = (
            select(EventRSVP)
            .options(selectinload(EventRSVP.event))
            .where(EventRSVP.user_id == user_id)
            .order_by(EventRSVP.created_at.desc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def next_attending_seat(self, event_id: uuid.UUID) -> int:
        """Smallest unused seat in [1..capacity]. Capacity itself is enforced by the caller."""
        stmt = select(func.coalesce(func.max(func.lower(EventRSVP.slot_range)), 0)).where(
            EventRSVP.event_id == event_id,
            EventRSVP.rsvp_status == "attending",
            EventRSVP.slot_range.is_not(None),
        )
        highest = (await self.db.execute(stmt)).scalar_one()
        return int(highest or 0) + 1

    async def unpublished_ready_to_announce(self) -> list[Event]:
        stmt = select(Event).where(
            Event.is_published.is_(True),
            Event.announced_at.is_(None),
        )
        return list((await self.db.execute(stmt)).scalars().all())


class ScholarshipRepository(BaseRepository[Scholarship]):
    def __init__(self, db: AsyncSession):
        super().__init__(Scholarship, db)

    async def list_scholarships(self, published_only: bool = True, open_only: bool = False) -> list[Scholarship]:
        stmt = select(Scholarship)
        if published_only:
            stmt = stmt.where(Scholarship.is_published.is_(True))
        if open_only:
            stmt = stmt.where(Scholarship.deadline >= func.current_date())
        stmt = stmt.order_by(Scholarship.deadline.asc())
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_application(
        self, scholarship_id: uuid.UUID, applicant_id: uuid.UUID
    ) -> ScholarshipApplication | None:
        stmt = select(ScholarshipApplication).where(
            ScholarshipApplication.scholarship_id == scholarship_id,
            ScholarshipApplication.applicant_id == applicant_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_application_by_id(self, application_id: uuid.UUID) -> ScholarshipApplication | None:
        stmt = (
            select(ScholarshipApplication)
            .options(selectinload(ScholarshipApplication.scholarship))
            .where(ScholarshipApplication.id == application_id)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_user_applications(self, applicant_id: uuid.UUID) -> list[ScholarshipApplication]:
        stmt = (
            select(ScholarshipApplication)
            .options(selectinload(ScholarshipApplication.scholarship))
            .where(ScholarshipApplication.applicant_id == applicant_id)
            .order_by(ScholarshipApplication.created_at.desc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def list_applications(self, scholarship_id: uuid.UUID | None = None) -> list[ScholarshipApplication]:
        stmt = select(ScholarshipApplication).options(selectinload(ScholarshipApplication.scholarship))
        if scholarship_id:
            stmt = stmt.where(ScholarshipApplication.scholarship_id == scholarship_id)
        stmt = stmt.order_by(ScholarshipApplication.created_at.desc())
        return list((await self.db.execute(stmt)).scalars().all())


class MentorshipRepository(BaseRepository[MentorshipPair]):
    def __init__(self, db: AsyncSession):
        super().__init__(MentorshipPair, db)

    async def get_pair(self, mentor_id: uuid.UUID, mentee_id: uuid.UUID) -> MentorshipPair | None:
        stmt = select(MentorshipPair).where(
            MentorshipPair.mentor_id == mentor_id,
            MentorshipPair.mentee_id == mentee_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_for_user(self, user_id: uuid.UUID) -> list[MentorshipPair]:
        stmt = (
            select(MentorshipPair)
            .where(or_(MentorshipPair.mentor_id == user_id, MentorshipPair.mentee_id == user_id))
            .order_by(MentorshipPair.created_at.desc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def list_open_mentors(self, exclude_user_id: uuid.UUID) -> list[AlumniProfile]:
        stmt = (
            select(AlumniProfile)
            .options(selectinload(AlumniProfile.user))
            .where(
                AlumniProfile.user_id != exclude_user_id,
                AlumniProfile.membership_status == "active",
                AlumniProfile.is_visible.is_(True),
            )
            .order_by(AlumniProfile.batch_year.asc())
        )
        return list((await self.db.execute(stmt)).scalars().all())


class NewsRepository(BaseRepository[NewsPost]):
    def __init__(self, db: AsyncSession):
        super().__init__(NewsPost, db)

    async def list_posts(self, published_only: bool = True, limit: int = 20) -> list[NewsPost]:
        stmt = select(NewsPost)
        if published_only:
            stmt = stmt.where(NewsPost.is_published.is_(True))
        stmt = stmt.order_by(func.coalesce(NewsPost.published_at, NewsPost.created_at).desc()).limit(limit)
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_by_slug(self, slug: str) -> NewsPost | None:
        stmt = select(NewsPost).where(NewsPost.slug == slug)
        return (await self.db.execute(stmt)).scalar_one_or_none()


class GalleryRepository(BaseRepository[GalleryAlbum]):
    def __init__(self, db: AsyncSession):
        super().__init__(GalleryAlbum, db)

    async def list_albums(self, published_only: bool = True) -> list[GalleryAlbum]:
        stmt = select(GalleryAlbum).options(selectinload(GalleryAlbum.photos))
        if published_only:
            stmt = stmt.where(GalleryAlbum.is_published.is_(True))
        stmt = stmt.order_by(GalleryAlbum.created_at.desc())
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_album(self, album_id: uuid.UUID) -> GalleryAlbum | None:
        stmt = (
            select(GalleryAlbum)
            .options(selectinload(GalleryAlbum.photos))
            .where(GalleryAlbum.id == album_id)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_photo(self, photo_id: uuid.UUID) -> GalleryPhoto | None:
        return await self.db.get(GalleryPhoto, photo_id)


class AlumniStatsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def landing_counts(self) -> dict[str, int]:
        active = select(func.count(AlumniProfile.id)).where(
            AlumniProfile.membership_status == "active"
        )
        events = select(func.count(Event.id)).where(Event.is_published.is_(True))
        scholarships = select(func.count(Scholarship.id)).where(
            Scholarship.is_published.is_(True),
            Scholarship.deadline >= func.current_date(),
        )
        news = select(func.count(NewsPost.id)).where(NewsPost.is_published.is_(True))
        batches = select(func.count(func.distinct(AlumniProfile.batch_year))).where(
            AlumniProfile.membership_status == "active"
        )
        return {
            "active_alumni": int((await self.db.execute(active)).scalar_one() or 0),
            "published_events": int((await self.db.execute(events)).scalar_one() or 0),
            "open_scholarships": int((await self.db.execute(scholarships)).scalar_one() or 0),
            "published_news": int((await self.db.execute(news)).scalar_one() or 0),
            "batches": int((await self.db.execute(batches)).scalar_one() or 0),
        }
