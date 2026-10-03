"""Alumni Portal business logic: registration, verification, and members area.

Layering follows the rest of the portal: endpoints validate with Pydantic,
delegate here, and this service talks only to repositories. Endpoint modules
never touch the ORM directly.

## Approval semantics (mirrors the teacher/CR/ER flow deliberately)

The existing ``AuthService`` creates teacher/CR/ER accounts with
``is_active=False`` and ``AuthService.approve_user`` flips them to
``True``. ``AuthService.authenticate`` refuses an inactive account with the
*same* generic message as a bad password, so a pending applicant cannot
distinguish "not approved yet" from "no such account".

Alumni follow that same shape rather than inventing a third gate:

- A new alumni claim starts ``membership_status='pending'`` and the backing
  user row is created ``is_active=False`` -- the claim is unverifiable until
  an admin says so, and nothing gated on identity is exposed before that.
- Approval sets ``membership_status='active'``, ``verified_by_admin=True``
  *and* ``user.is_active=True``, so the member can finally log in.
- Rejection sets ``membership_status='rejected'`` and leaves the user
  inactive, so the account still cannot get in.

The one deliberate difference from the teacher flow: an alumni *rejection*
is recorded on the profile (``rejected``) rather than being a no-op, because
the portal needs to show the applicant a decision and the directory must be
able to exclude them. Resubmission after a rejection is intentionally NOT
allowed here (see :meth:`AlumniService.register`); that policy is a product
decision flagged to the user, not something this layer should decide silently.
"""
from __future__ import annotations

import re
import uuid
from datetime import date, datetime, timezone

from sqlalchemy.exc import OperationalError, ProgrammingError

from app.core.exceptions import (
    ForbiddenException,
    NotFoundException,
    ResourceConflictException,
)
from app.models.alumni import (
    AlumniProfile,
    Event,
    EventRSVP,
    MembershipStatus,
    MentorshipPair,
    Scholarship,
    ScholarshipApplication,
)
from app.models.user import User, UserRole
from app.repositories.alumni_repository import (
    AlumniRepository,
    AlumniStatsRepository,
    EventRepository,
    GalleryRepository,
    MentorshipRepository,
    NewsRepository,
    ScholarshipRepository,
)
from app.repositories.user_repository import UserRepository
from app.schemas.alumni import (
    AlumniDashboardResponse,
    AlumniLandingResponse,
    AlumniLandingStats,
    AlumniProfileCreate,
    AlumniProfileResponse,
    AlumniProfileUpdate,
    AlumniRegisterRequest,
    AlumniVerificationDecision,
    EventCreate,
    EventResponse,
    EventRsvpRequest,
    EventRsvpResponse,
    GalleryAlbumResponse,
    MentorshipPairResponse,
    MentorshipRequest,
    MentorshipRespondRequest,
    NewsPostResponse,
    ScholarshipApplyRequest,
    ScholarshipApplicationResponse,
    ScholarshipCreate,
    ScholarshipResponse,
    ScholarshipReviewRequest,
)
from app.schemas.auth import RegisterResponse


def _aware(value: datetime | None) -> datetime | None:
    """Normalise naive SQLite timestamps so window comparisons do not TypeError."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "post"


class AlumniService:
    def __init__(self, db):
        self.db = db
        self.repo = AlumniRepository(db)
        self.users = UserRepository(db)
        self.events = EventRepository(db)
        self.scholarships = ScholarshipRepository(db)
        self.mentorship = MentorshipRepository(db)
        self.news = NewsRepository(db)
        self.gallery = GalleryRepository(db)
        self.stats = AlumniStatsRepository(db)

    async def register(self, dto: AlumniRegisterRequest) -> RegisterResponse:
        """Create a fresh alumni account plus its pending verification claim.

        Deliberately refuses to attach an alumni profile to an *existing*
        account (student/CR/teacher converting after graduation is a product
        question, not a silent implementation detail). A conflicting email or
        identifier is a 409 rather than an ownership transfer, so this can
        never be used to hijack someone else's account.
        """
        from app.core.security import create_upload_token, get_password_hash

        if await self.users.get_by_email(dto.email):
            raise ResourceConflictException("Email already in use.")

        identifier = f"alum-{uuid.uuid4().hex[:8]}"
        user = User(
            identifier=identifier,
            email=dto.email,
            full_name=dto.full_name,
            password_hash=await get_password_hash(dto.password),
            role=UserRole.ALUMNI,
            # Pending verification, same as teacher/CR/ER. Authenticated
            # access stays closed until an admin approves (see module docstring).
            is_active=False,
        )
        await self.users.create(user)

        self.db.add(
            AlumniProfile(
                user_id=user.id,
                batch_year=dto.batch_year,
                department=dto.department,
                graduation_date=dto.graduation_date,
                current_company=dto.current_company,
                designation=dto.designation,
                industry=dto.industry,
                linkedin_url=dto.linkedin_url,
                verified_by_admin=False,
                membership_status=MembershipStatus.PENDING.value,
                # Directory visibility is a separate, explicit opt-in from
                # verification, so an approved member is not published by
                # default. is_visible is never taken from this request.
                is_visible=False,
            )
        )
        await self.db.commit()
        return RegisterResponse(
            message="Registered. Awaiting admin verification of your alumni claim.",
            requires_approval=True,
            upload_token=create_upload_token(str(user.id)),
        )

    async def submit_claim(self, user: User, dto: AlumniProfileCreate) -> AlumniProfileResponse:
        """Attach a batch/department claim to the current user's account.

        Used by an already-authenticated portal user who was not created
        through alumni registration. The claim always starts ``pending``.
        """
        existing = await self.repo.get_profile_by_user_id(user.id)
        if existing:
            raise ResourceConflictException(
                "An alumni claim already exists for this account."
            )

        profile = AlumniProfile(
            user_id=user.id,
            batch_year=dto.batch_year,
            department=dto.department,
            graduation_date=dto.graduation_date,
            current_company=dto.current_company,
            designation=dto.designation,
            industry=dto.industry,
            linkedin_url=dto.linkedin_url,
            verified_by_admin=False,
            membership_status=MembershipStatus.PENDING.value,
            is_visible=bool(dto.is_visible),
        )
        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)
        return AlumniProfileResponse.model_validate(profile)

    async def get_my_profile(self, user: User) -> AlumniProfileResponse | None:
        profile = await self.repo.get_profile_by_user_id(user.id)
        if not profile:
            return None
        return AlumniProfileResponse.model_validate(profile)

    async def update_my_profile(self, user: User, dto: AlumniProfileUpdate) -> AlumniProfileResponse:
        profile = await self.repo.get_profile_by_user_id(user.id)
        if not profile:
            raise NotFoundException("Alumni profile not found.")
        data = dto.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(profile, key, value)
        await self.db.commit()
        await self.db.refresh(profile)
        return AlumniProfileResponse.model_validate(profile)

    async def list_pending_verifications(self) -> list[AlumniProfileResponse]:
        """Queue for the admin verification view.

        Filters on ``membership_status='pending'`` (not ``is_active``): an
        already-decided claim must not reappear in the queue just because the
        backing user is still inactive.
        """
        profiles = await self.repo.list_pending_verifications()
        return [AlumniProfileResponse.model_validate(p) for p in profiles]

    async def approve(self, profile_id: uuid.UUID, admin: User) -> AlumniProfileResponse:
        profile = await self._get_decidable(profile_id)
        profile.membership_status = MembershipStatus.ACTIVE.value
        profile.verified_by_admin = True
        # Mirror AuthService.approve_user: approval is what activates the
        # account, so a pending alumnus can only log in after this point.
        user = await self.users.get_by_id(profile.user_id)
        if user:
            user.is_active = True
        await self.db.commit()
        await self.db.refresh(profile)
        return AlumniProfileResponse.model_validate(profile)

    async def reject(
        self, profile_id: uuid.UUID, admin: User, dto: AlumniVerificationDecision | None = None
    ) -> AlumniProfileResponse:
        """Record a refused claim and keep the account closed.

        The user row is left ``is_active=False`` -- a rejected claimant is not
        a member, so flipping that flag would hand them a working session.
        The reason is accepted but not stored: ``alumni_profiles`` has no
        column for it, and adding one is a schema decision, not a silent
        extra. Tracked for the user below.
        """
        profile = await self._get_decidable(profile_id)
        profile.membership_status = MembershipStatus.REJECTED.value
        profile.verified_by_admin = False
        user = await self.users.get_by_id(profile.user_id)
        if user:
            user.is_active = False
        await self.db.commit()
        await self.db.refresh(profile)
        return AlumniProfileResponse.model_validate(profile)

    async def _get_decidable(self, profile_id: uuid.UUID) -> AlumniProfile:
        profile = await self.repo.get_profile(profile_id)
        if not profile:
            raise NotFoundException("Alumni claim not found.")
        if profile.membership_status != MembershipStatus.PENDING.value:
            # Approving or rejecting a decided claim would silently rewrite an
            # admin's earlier decision.
            raise ResourceConflictException(
                "This claim has already been decided."
            )
        return profile

    async def landing(self) -> AlumniLandingResponse:
        """Public landing payload: only published / visible content."""
        counts = await self.stats.landing_counts()
        news = await self.news.list_posts(published_only=True, limit=4)
        events = await self.events.list_events(published_only=True, upcoming_only=False)
        scholarships = await self.scholarships.list_scholarships(published_only=True, open_only=True)
        gallery = await self.gallery.list_albums(published_only=True)
        event_payloads = [await self._event_response(item) for item in events[:4]]
        return AlumniLandingResponse(
            stats=AlumniLandingStats(**counts),
            news=[NewsPostResponse.model_validate(item) for item in news],
            events=event_payloads,
            gallery=[GalleryAlbumResponse.model_validate(item) for item in gallery[:6]],
            scholarships=[ScholarshipResponse.model_validate(item) for item in scholarships[:4]],
        )

    async def dashboard(self, user: User) -> AlumniDashboardResponse:
        profile = await self.repo.get_profile_by_user_id(user.id)
        rsvps = await self.events.list_user_rsvps(user.id)
        applications = await self.scholarships.list_user_applications(user.id)
        pairs = await self.mentorship.list_for_user(user.id)
        return AlumniDashboardResponse(
            profile=AlumniProfileResponse.model_validate(profile) if profile else None,
            events=[await self._rsvp_response(item) for item in rsvps],
            applications=[ScholarshipApplicationResponse.model_validate(item) for item in applications],
            mentorship=[MentorshipPairResponse.model_validate(item) for item in pairs],
            pending_verification=bool(profile and profile.membership_status == MembershipStatus.PENDING.value),
        )

    async def search_directory(
        self,
        q: str | None = None,
        batch_year: int | None = None,
        industry: str | None = None,
        limit: int = 50,
    ) -> list[AlumniProfileResponse]:
        try:
            rows = await self.repo.search_directory(
                q=q, batch_year=batch_year, industry=industry, visible_only=True,
                membership_status=MembershipStatus.ACTIVE.value, limit=min(limit, 100),
            )
        except (ProgrammingError, OperationalError):
            await self.db.rollback()
            rows = await self.repo.search_directory_fallback(
                q=q, batch_year=batch_year, industry=industry, visible_only=True,
                membership_status=MembershipStatus.ACTIVE.value, limit=min(limit, 100),
            )
        return [AlumniProfileResponse.model_validate(row) for row in rows]

    async def get_directory_profile(self, profile_id: uuid.UUID) -> AlumniProfileResponse:
        profile = await self.repo.get_profile(profile_id)
        if (
            not profile
            or not profile.is_visible
            or profile.membership_status != MembershipStatus.ACTIVE.value
        ):
            raise NotFoundException("Alumni profile not found.")
        return AlumniProfileResponse.model_validate(profile)

    async def list_events(self, user: User | None = None) -> list[EventResponse]:
        published_only = not (user and user.role == UserRole.SUPER_ADMIN)
        rows = await self.events.list_events(published_only=published_only)
        return [await self._event_response(row) for row in rows]

    async def get_event(self, event_id: uuid.UUID, user: User | None = None) -> EventResponse:
        event = await self.events.get_event(event_id)
        if not event:
            raise NotFoundException("Event not found.")
        if not event.is_published and not (user and user.role == UserRole.SUPER_ADMIN):
            raise NotFoundException("Event not found.")
        return await self._event_response(event)

    async def create_event(self, admin: User, dto: EventCreate) -> EventResponse:
        event = Event(created_by=admin.id, **dto.model_dump())
        await self.events.create(event)
        await self.db.commit()
        await self.db.refresh(event)
        return await self._event_response(event)

    async def rsvp_event(self, user: User, event_id: uuid.UUID, dto: EventRsvpRequest) -> EventRsvpResponse:
        event = await self.events.get_event(event_id)
        if not event or not event.is_published:
            raise NotFoundException("Event not found.")
        if event.members_only and user.role != UserRole.ALUMNI:
            raise ForbiddenException("This event is limited to verified alumni.")

        existing = await self.events.get_rsvp(event_id, user.id)
        if existing:
            existing.rsvp_status = dto.rsvp_status
            existing.note = dto.note
            if dto.rsvp_status != "attending":
                existing.slot_range = None
            elif event.capacity is not None and existing.slot_range is None:
                await self._assign_seat(event)
            await self.db.commit()
            await self.db.refresh(existing)
            return await self._rsvp_response(existing)

        if dto.rsvp_status == "attending" and event.capacity is not None:
            await self._assign_seat(event)

        rsvp = EventRSVP(
            event_id=event.id,
            user_id=user.id,
            rsvp_status=dto.rsvp_status,
            note=dto.note,
        )
        self.db.add(rsvp)
        await self.db.commit()
        await self.db.refresh(rsvp)
        return await self._rsvp_response(rsvp)

    async def _assign_seat(self, event: Event) -> None:
        attending = await self.events.attending_count(event.id)
        if event.capacity is not None and attending >= event.capacity:
            raise ResourceConflictException("This event is at capacity.")
        # SQLite has no INT4RANGE; leave slot_range null and rely on the
        # count check above. Postgres can still apply the GiST exclusion.
        return None

    async def list_scholarships(self, user: User | None = None) -> list[ScholarshipResponse]:
        published_only = not (user and user.role == UserRole.SUPER_ADMIN)
        rows = await self.scholarships.list_scholarships(published_only=published_only)
        return [ScholarshipResponse.model_validate(row) for row in rows]

    async def create_scholarship(self, admin: User, dto: ScholarshipCreate) -> ScholarshipResponse:
        item = Scholarship(created_by=admin.id, **dto.model_dump())
        await self.scholarships.create(item)
        await self.db.commit()
        await self.db.refresh(item)
        return ScholarshipResponse.model_validate(item)

    async def apply_scholarship(
        self, user: User, scholarship_id: uuid.UUID, dto: ScholarshipApplyRequest
    ) -> ScholarshipApplicationResponse:
        scholarship = await self.scholarships.get_by_id(scholarship_id)
        if not scholarship or not scholarship.is_published:
            raise NotFoundException("Scholarship not found.")
        if scholarship.deadline < date.today():
            raise ResourceConflictException("The application deadline has passed.")
        existing = await self.scholarships.get_application(scholarship_id, user.id)
        if existing:
            raise ResourceConflictException("You have already applied for this scholarship.")
        application = ScholarshipApplication(
            scholarship_id=scholarship.id,
            applicant_id=user.id,
            motivation=dto.motivation,
            document_key=dto.document_key,
            document_name=dto.document_name,
            status="submitted",
        )
        self.db.add(application)
        await self.db.commit()
        await self.db.refresh(application)
        return ScholarshipApplicationResponse.model_validate(application)

    async def review_application(
        self, admin: User, application_id: uuid.UUID, dto: ScholarshipReviewRequest
    ) -> ScholarshipApplicationResponse:
        application = await self.scholarships.get_application_by_id(application_id)
        if not application:
            raise NotFoundException("Application not found.")
        application.status = dto.status
        application.reviewed_by = admin.id
        application.reviewed_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(application)
        return ScholarshipApplicationResponse.model_validate(application)

    async def list_mentors(self, user: User) -> list[AlumniProfileResponse]:
        rows = await self.mentorship.list_open_mentors(user.id)
        return [AlumniProfileResponse.model_validate(row) for row in rows]

    async def request_mentorship(self, user: User, dto: MentorshipRequest) -> MentorshipPairResponse:
        if dto.mentor_id == user.id:
            raise ResourceConflictException("You cannot mentor yourself.")
        mentor = await self.users.get_by_id(dto.mentor_id)
        if not mentor or mentor.role != UserRole.ALUMNI:
            raise NotFoundException("Mentor not found.")
        mentor_profile = await self.repo.get_profile_by_user_id(mentor.id)
        if (
            not mentor_profile
            or mentor_profile.membership_status != MembershipStatus.ACTIVE.value
            or not mentor_profile.is_visible
        ):
            raise NotFoundException("Mentor not found.")
        existing = await self.mentorship.get_pair(mentor.id, user.id)
        if existing:
            raise ResourceConflictException("A mentorship request already exists.")
        pair = MentorshipPair(
            mentor_id=mentor.id,
            mentee_id=user.id,
            requested_by=user.id,
            mentee_note=dto.mentee_note,
            status="requested",
        )
        await self.mentorship.create(pair)
        await self.db.commit()
        await self.db.refresh(pair)
        return MentorshipPairResponse.model_validate(pair)

    async def respond_mentorship(
        self, user: User, pair_id: uuid.UUID, accept: bool, dto: MentorshipRespondRequest | None = None
    ) -> MentorshipPairResponse:
        pair = await self.mentorship.get_by_id(pair_id)
        if not pair:
            raise NotFoundException("Mentorship request not found.")
        if pair.mentor_id != user.id:
            raise ForbiddenException("Only the requested mentor can respond.")
        if pair.status != "requested":
            raise ResourceConflictException("This mentorship request has already been decided.")
        pair.status = "active" if accept else "declined"
        pair.mentor_note = dto.mentor_note if dto else None
        if accept:
            pair.started_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(pair)
        return MentorshipPairResponse.model_validate(pair)

    async def list_news(self) -> list[NewsPostResponse]:
        rows = await self.news.list_posts(published_only=True, limit=20)
        return [NewsPostResponse.model_validate(row) for row in rows]

    async def get_news(self, slug: str) -> NewsPostResponse:
        post = await self.news.get_by_slug(slug)
        if not post or not post.is_published:
            raise NotFoundException("News post not found.")
        return NewsPostResponse.model_validate(post)

    async def list_gallery(self) -> list[GalleryAlbumResponse]:
        rows = await self.gallery.list_albums(published_only=True)
        return [GalleryAlbumResponse.model_validate(row) for row in rows]

    async def _event_response(self, event: Event) -> EventResponse:
        attending = await self.events.attending_count(event.id)
        payload = EventResponse.model_validate(event)
        payload.attending_count = attending
        return payload

    async def _rsvp_response(self, rsvp: EventRSVP) -> EventRsvpResponse:
        payload = EventRsvpResponse.model_validate(rsvp)
        if rsvp.event is not None:
            payload.event = await self._event_response(rsvp.event)
        return payload
