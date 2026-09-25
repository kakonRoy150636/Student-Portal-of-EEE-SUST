"""Alumni Portal business logic: registration, verification queue, decisions.

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

import uuid

from app.core.exceptions import NotFoundException, ResourceConflictException
from app.models.alumni import AlumniProfile, MembershipStatus
from app.models.user import User, UserRole
from app.repositories.alumni_repository import AlumniRepository
from app.repositories.user_repository import UserRepository
from app.schemas.alumni import (
    AlumniProfileCreate,
    AlumniProfileResponse,
    AlumniRegisterRequest,
    AlumniVerificationDecision,
)
from app.schemas.auth import RegisterResponse


class AlumniService:
    def __init__(self, db):
        self.db = db
        self.repo = AlumniRepository(db)
        self.users = UserRepository(db)

    async def register(self, dto: AlumniRegisterRequest) -> "RegisterResponse":
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
            password_hash=get_password_hash(dto.password),
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

    async def get_my_profile(self, user: User) -> "AlumniProfileResponse | None":
        profile = await self.repo.get_profile_by_user_id(user.id)
        if not profile:
            return None
        return AlumniProfileResponse.model_validate(profile)

    async def list_pending_verifications(self) -> list["AlumniProfileResponse"]:
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
