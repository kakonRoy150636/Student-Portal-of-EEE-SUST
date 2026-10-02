import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.user_repository import UserRepository
from app.core.security import (
    create_access_token,
    create_mfa_token,
    create_upload_token,
    generate_random_token,
    hash_secret_token,
)
from app.core.passwords import hash_password, verify_password_async
from app.core.config import settings
from app.core.mfa import (
    generate_recovery_codes,
    generate_totp_secret,
    provisioning_uri,
    recovery_codes_match,
    verify_totp,
)
from app.core.exceptions import (
    UnauthorizedException,
    ForbiddenException,
    ResourceConflictException,
    NotFoundException,
    ValidationException,
)
from app.core.rate_limit import verify_attempt
from app.schemas.auth import (
    LoginRequest, AuthSessionResponse, TokenResponse, UserResponse,
    TeacherRegisterRequest, StudentRegisterRequest, RegisterResponse,
    SessionSummary,
)
from app.models.user import User, UserRole, StudentProfile, FacultyProfile
from app.models.auth import PasswordResetToken, RefreshToken
from app.models.academic import CourseEnrollment, CourseOffering
from app.services.audit_service import AuditService

import structlog

logger = structlog.get_logger(__name__)


def _client_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    from app.api.dependencies import get_client_ip

    return get_client_ip(request)


def _user_agent(request: Request | None) -> str | None:
    if request is None:
        return None
    value = request.headers.get("user-agent")
    return value[:255] if value else None


def _decode_mfa_token(token: str) -> uuid.UUID | None:
    """Validate an MFA challenge token and return the user id it names."""
    import jwt as pyjwt

    try:
        payload = pyjwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except pyjwt.PyJWTError:
        return None
    if payload.get("type") != "mfa":
        return None
    try:
        return uuid.UUID(payload.get("sub"))
    except (TypeError, ValueError, AttributeError):
        return None


def _hash_recovery_code(code: str) -> str:
    from app.core.mfa import hash_recovery_code

    return hash_recovery_code(code)


@dataclass
class AuthenticationOutcome:
    """Result of a credential check: a session, or the MFA challenge."""

    session: AuthSessionResponse | None = None
    refresh_token: str | None = None
    mfa_token: str | None = None

    @property
    def mfa_required(self) -> bool:
        return self.mfa_token is not None


def _is_expired(expires_at: datetime) -> bool:
    """Whether a refresh token's expiry has passed.

    ``expires_at`` is TIMESTAMPTZ in Postgres (asyncpg hands back aware
    datetimes), but SQLite -- used by the test suite -- has no timezone-aware
    storage and returns naive values. Comparing either against an aware
    ``datetime.now(timezone.utc)`` raises TypeError, which would surface as a
    500 instead of a normal "expired" rejection, so the two are normalised
    before comparing.
    """
    if expires_at.tzinfo is None:
        # Naive value: compare both sides as naive UTC.
        return expires_at < datetime.now(timezone.utc).replace(tzinfo=None)
    return expires_at < datetime.now(timezone.utc)


# How long after a rotation a duplicate presentation of the old refresh token
# is assumed to be a race between two tabs rather than a stolen token.
REFRESH_RACE_GRACE_SECONDS = 15


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = UserRepository(db)

    async def _issue_refresh_token(
        self,
        user_id: uuid.UUID,
        family: uuid.UUID | None = None,
        request: Request | None = None,
    ) -> str:
        """Persist a hashed refresh token and return the plaintext one.

        If ``family`` is None a new token family is started; otherwise the new
        token joins the existing family (rotation). The request's IP and
        user-agent are stored so /auth/sessions can show the account holder
        which devices are signed in.
        """
        token = generate_random_token()
        await self.db.execute(
            RefreshToken.__table__.insert().values(
                user_id=user_id,
                token_family=family or uuid.uuid4(),
                token_hash=hash_secret_token(token),
                is_revoked=False,
                expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
                last_used_at=datetime.now(timezone.utc),
                ip_address=_client_ip(request),
                user_agent=_user_agent(request),
            )
        )
        return token

    async def _revoke_family(self, family: uuid.UUID) -> None:
        """Revoke every token in a family (reuse detection / logout)."""
        stmt = (
            RefreshToken.__table__.update()
            .where(RefreshToken.token_family == family)
            .values(is_revoked=True)
        )
        await self.db.execute(stmt)

    async def authenticate(
        self, dto: LoginRequest, client_ip: str = "unknown", request: Request | None = None
    ) -> AuthenticationOutcome:
        user = await self.repo.get_by_identifier(dto.identifier)
        # `verify_password_async` always performs a bcrypt comparison -- against
        # a fixed dummy hash when the account does not exist -- so a missing
        # identifier costs the same wall time as a wrong password. The uniform
        # error message below is otherwise undermined by response timing.
        # bcrypt itself runs in a worker thread, so the 150-300 ms of CPU it
        # needs cannot stall every other request on this event loop.
        password_ok = await verify_password_async(dto.password, user.password_hash if user else None)

        # The delay is applied *after* the password check, and only for wrong
        # credentials. Doing it beforehand (as the first attempt did) meant a
        # correct password could be made to wait for failures it had nothing
        # to do with, which turned the throttle into a tool for locking any
        # known account out of its own password.
        await verify_attempt(dto.identifier, password_ok, client_ip)

        # Every failure below reports the same message, so a caller cannot
        # enumerate which identifiers exist. This also covers what used to be
        # a distinct "awaiting admin approval" string, which confirmed that
        # a given email belonged to a real, unapproved teacher/CR/ER account.
        if not password_ok or not user.is_active:
            await AuditService(self.db).record(
                action="auth.login_failed",
                entity_type="user",
                entity_id=user.id if user else None,
                actor_id=user.id if user else None,
                detail={"identifier_supplied": dto.identifier[:64]},
                request=request,
                commit=True,
            )
            raise UnauthorizedException("Invalid institutional identifier or password.")

        # Enrolled second factor: hand back a challenge instead of a session.
        # The password has already been verified, so a wrong code at the next
        # step cannot be used to probe for account existence.
        if user.mfa_enabled and user.mfa_secret:
            await AuditService(self.db).record(
                action="auth.mfa_challenge_issued",
                entity_type="user",
                entity_id=user.id,
                actor_id=user.id,
                request=request,
                commit=True,
            )
            return AuthenticationOutcome(mfa_token=create_mfa_token(str(user.id)))

        token = create_access_token({"sub": str(user.id), "role": user.role.value})
        refresh = await self._issue_refresh_token(user.id, request=request)
        await self.db.commit()
        return AuthenticationOutcome(
            session=AuthSessionResponse(
                user=UserResponse.model_validate(user),
                tokens=TokenResponse(access_token=token),
            ),
            refresh_token=refresh,
        )

    async def verify_mfa_login(
        self, mfa_token: str, code: str, request: Request | None = None
    ) -> AuthenticationOutcome:
        """Second step of a two-factor login: TOTP code or a recovery code."""
        user_id = _decode_mfa_token(mfa_token)
        if user_id is None:
            raise UnauthorizedException("The verification session has expired. Sign in again.")

        user = await self.repo.get_by_id(user_id)
        if not user or not user.is_active or not user.mfa_enabled or not user.mfa_secret:
            raise UnauthorizedException("The verification session has expired. Sign in again.")

        audit = AuditService(self.db)
        if verify_totp(user.mfa_secret, code):
            pass
        else:
            # Allow a one-time recovery code, and consume it on use so it
            # cannot be replayed.
            matched = recovery_codes_match(user.mfa_recovery_hashes, code)
            if matched is None:
                await audit.record(
                    action="auth.mfa_failed",
                    entity_type="user",
                    entity_id=user.id,
                    actor_id=user.id,
                    request=request,
                    commit=True,
                )
                raise UnauthorizedException("That code is not valid.")
            remaining = [h for h in (user.mfa_recovery_hashes or []) if h != matched]
            user.mfa_recovery_hashes = remaining
            await audit.record(
                action="auth.mfa_recovery_code_used",
                entity_type="user",
                entity_id=user.id,
                actor_id=user.id,
                detail={"remaining_codes": len(remaining)},
                request=request,
            )

        access = create_access_token({"sub": str(user.id), "role": user.role.value})
        refresh = await self._issue_refresh_token(user.id, request=request)
        await audit.record(
            action="auth.login",
            entity_type="user",
            entity_id=user.id,
            actor_id=user.id,
            detail={"mfa": True},
            request=request,
        )
        await self.db.commit()
        return AuthenticationOutcome(
            session=AuthSessionResponse(
                user=UserResponse.model_validate(user),
                tokens=TokenResponse(access_token=access),
            ),
            refresh_token=refresh,
        )

    # ------------------------------------------------------------------ MFA
    async def start_mfa_setup(self, user: User) -> dict[str, str]:
        """Generate (but do not yet trust) a TOTP secret for this account."""
        secret = generate_totp_secret()
        user.mfa_secret = secret
        user.mfa_enabled = False
        await self.db.commit()
        return {"secret": secret, "otpauth_uri": provisioning_uri(secret, user.email)}

    async def enable_mfa(self, user: User, code: str, request: Request | None = None) -> list[str]:
        """Confirm enrolment and mint one-time recovery codes."""
        if not user.mfa_secret:
            raise ValidationException("Start the setup before confirming a code.")
        if not verify_totp(user.mfa_secret, code):
            raise ValidationException("That code is not valid. Check the time on your device.")

        codes = generate_recovery_codes()
        user.mfa_recovery_hashes = [_hash_recovery_code(c) for c in codes]
        user.mfa_enabled = True
        await AuditService(self.db).record(
            action="auth.mfa_enabled",
            entity_type="user",
            entity_id=user.id,
            actor_id=user.id,
            request=request,
        )
        await self.db.commit()
        # Plaintext recovery codes are returned exactly once and never stored.
        return codes

    async def disable_mfa(self, user: User, password: str, request: Request | None = None) -> None:
        if not await verify_password_async(password, user.password_hash):
            raise UnauthorizedException("Password is incorrect.")
        user.mfa_enabled = False
        user.mfa_secret = None
        user.mfa_recovery_hashes = None
        await AuditService(self.db).record(
            action="auth.mfa_disabled",
            entity_type="user",
            entity_id=user.id,
            actor_id=user.id,
            request=request,
        )
        await self.db.commit()

    # --------------------------------------------------------------- password
    async def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str,
        request: Request | None = None,
    ) -> AuthenticationOutcome:
        """Replace a password and end every other session.

        Used both by the ordinary "change my password" screen and by accounts
        carrying ``must_change_password`` (the bootstrap administrator, or
        someone who just completed a reset)- the flag is cleared here.
        """
        if not await verify_password_async(current_password, user.password_hash):
            raise UnauthorizedException("Current password is incorrect.")
        if await verify_password_async(new_password, user.password_hash):
            raise ValidationException("The new password must differ from the current one.")

        user.password_hash = await hash_password(new_password)
        was_forced = bool(user.must_change_password)
        user.must_change_password = False

        # Changing a password is a response to a possible compromise as often
        # as it is routine. Every refresh token issued with the old password is
        # therefore revoked -- the caller gets a fresh session below.
        await self._revoke_all_families(user.id)
        refresh = await self._issue_refresh_token(user.id, request=request)
        await AuditService(self.db).record(
            action="auth.password_changed",
            entity_type="user",
            entity_id=user.id,
            actor_id=user.id,
            detail={"forced_at_first_login": was_forced},
            request=request,
        )
        await self.db.commit()

        access = create_access_token({"sub": str(user.id), "role": user.role.value})
        return AuthenticationOutcome(
            session=AuthSessionResponse(
                user=UserResponse.model_validate(user),
                tokens=TokenResponse(access_token=access),
            ),
            refresh_token=refresh,
        )

    async def request_password_reset(self, email: str, request: Request | None = None) -> None:
        """Create a reset token if the address belongs to an account.

        The caller always returns the same message; this method is deliberately
        silent about whether anything happened, so the endpoint cannot be used
        to enumerate accounts.
        """
        user = await self.repo.get_by_email(email)
        if not user or not user.is_active:
            return

        # One outstanding token per account: requesting a new link invalidates
        # any previous one, so an old email cannot be replayed.
        await self.db.execute(
            PasswordResetToken.__table__.update()
            .where(PasswordResetToken.user_id == user.id, PasswordResetToken.is_used.is_(False))
            .values(is_used=True)
        )
        token = generate_random_token()
        await self.db.execute(
            PasswordResetToken.__table__.insert().values(
                user_id=user.id,
                token_hash=hash_secret_token(token),
                is_used=False,
                expires_at=datetime.now(timezone.utc)
                + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_MINUTES),
            )
        )
        await AuditService(self.db).record(
            action="auth.password_reset_requested",
            entity_type="user",
            entity_id=user.id,
            actor_id=user.id,
            request=request,
        )
        await self.db.commit()

        from app.services.email_service import send_email  # local: avoids import cycle

        link = f"{settings.PUBLIC_APP_URL.rstrip('/')}/reset-password?token={token}"
        sent = await send_email(
            to=user.email,
            subject="Reset your SUST EEE portal password",
            body=(
                "Someone requested a password reset for this account.\n\n"
                f"Use this link within {settings.PASSWORD_RESET_TOKEN_MINUTES} minutes:\n{link}\n\n"
                "If this was not you, no action is needed."
            ),
        )
        if not sent and settings.ENVIRONMENT != "production":
            # Development convenience only: without SMTP there is no other way
            # to deliver the link. Production must configure SMTP instead of
            # shipping reset links into a log aggregator.
            logger.info("password_reset_link_dev_only", link=link)

    async def confirm_password_reset(
        self, token: str, new_password: str, request: Request | None = None
    ) -> None:
        token_hash = hash_secret_token(token)
        stored = (
            await self.db.execute(
                select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
            )
        ).scalar_one_or_none()
        if not stored or stored.is_used:
            raise ValidationException("This reset link is invalid or has already been used.")
        if _is_expired(stored.expires_at):
            raise ValidationException("This reset link has expired. Request a new one.")

        user = await self.repo.get_by_id(stored.user_id)
        if not user or not user.is_active:
            raise ValidationException("This reset link is invalid or has already been used.")

        user.password_hash = await hash_password(new_password)
        stored.is_used = True
        # A completed reset must not leave other sessions running: whoever
        # possessed the old password loses access with it.
        await self._revoke_all_families(user.id)
        await AuditService(self.db).record(
            action="auth.password_reset_completed",
            entity_type="user",
            entity_id=user.id,
            actor_id=user.id,
            request=request,
        )
        await self.db.commit()

    async def _revoke_all_families(self, user_id: uuid.UUID) -> None:
        await self.db.execute(
            RefreshToken.__table__.update()
            .where(RefreshToken.user_id == user_id, RefreshToken.is_revoked.is_(False))
            .values(is_revoked=True)
        )

    # --------------------------------------------------------------- sessions
    async def list_sessions(
        self, user: User, current_refresh_token: str | None
    ) -> list[SessionSummary]:
        """One entry per signed-in device (refresh-token family)."""
        rows = (
            (
                await self.db.execute(
                    select(RefreshToken)
                    .where(RefreshToken.user_id == user.id)
                    .order_by(RefreshToken.created_at.desc())
                )
            )
            .scalars()
            .all()
        )
        current_hash = hash_secret_token(current_refresh_token) if current_refresh_token else None

        families: dict[uuid.UUID, SessionSummary] = {}
        for row in rows:
            summary = families.get(row.token_family)
            if summary is None:
                summary = SessionSummary(
                    family_id=row.token_family,
                    created_at=row.created_at,
                    last_used_at=row.last_used_at,
                    ip_address=row.ip_address,
                    user_agent=row.user_agent,
                    # Flipped to True only if a live (unrevoked, unexpired)
                    # token is found below. Starting at True would report a
                    # family that is fully revoked as still active.
                    is_active=False,
                )
                families[row.token_family] = summary
            if row.token_hash == current_hash:
                summary.is_current = True
            if row.last_used_at and (
                summary.last_used_at is None or row.last_used_at > summary.last_used_at
            ):
                summary.last_used_at = row.last_used_at
            # A family is dead once every token in it is revoked or expired.
            if not row.is_revoked and not _is_expired(row.expires_at):
                summary.is_active = True
        return list(families.values())

    async def revoke_session(self, user: User, family_id: uuid.UUID) -> bool:
        result = await self.db.execute(
            RefreshToken.__table__.update()
            .where(RefreshToken.user_id == user.id, RefreshToken.token_family == family_id)
            .values(is_revoked=True)
        )
        await AuditService(self.db).record(
            action="auth.session_revoked",
            entity_type="session",
            entity_id=family_id,
            actor_id=user.id,
            detail={"tokens": result.rowcount},
        )
        await self.db.commit()
        return bool(result.rowcount)

    async def refresh_access_token(self, refresh_token: str) -> tuple[str, str]:
        """Rotate a refresh token:

        - Validate the presented token against the store.
        - Reject replay of an already-rotated/revoked token and revoke the whole
          family (token-theft detection).
        - Issue a new access token + a fresh refresh token in the same family.
        """
        token_hash = hash_secret_token(refresh_token)
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        stored = (await self.db.execute(stmt)).scalar_one_or_none()

        if not stored:
            raise UnauthorizedException("Refresh token is invalid.")
        if stored.is_revoked:
            if await self._recently_rotated(stored):
                # Two tabs (or a StrictMode double-effect) can present the same
                # cookie at almost the same moment; one rotation wins and the
                # loser arrives a beat later. Treating that as theft would log
                # the user out of every device for opening a second tab, so a
                # replay inside the grace window is rejected *without* revoking
                # the family. A replay after it still trips theft detection.
                raise UnauthorizedException("Refresh token has already been rotated.")
            await self._revoke_family(stored.token_family)
            await self.db.commit()
            raise UnauthorizedException("Refresh token has been revoked.")
        if _is_expired(stored.expires_at):
            await self._revoke_family(stored.token_family)
            await self.db.commit()
            raise UnauthorizedException("Refresh token has expired.")

        user = await self.repo.get_by_id(stored.user_id)
        if not user or not user.is_active:
            raise UnauthorizedException("User account is inactive.")

        await self._revoke_family(stored.token_family)
        new_refresh = await self._issue_refresh_token(user.id, family=stored.token_family)
        await self.db.commit()

        access = create_access_token({"sub": str(user.id), "role": user.role.value})
        return access, new_refresh

    async def _recently_rotated(self, stored: RefreshToken) -> bool:
        """Whether the family gained a token moments ago (a benign race)."""
        from sqlalchemy import func

        newest = (
            await self.db.execute(
                select(func.max(RefreshToken.created_at)).where(
                    RefreshToken.token_family == stored.token_family
                )
            )
        ).scalar_one_or_none()
        if newest is None or newest <= stored.created_at:
            return False
        now = datetime.now(timezone.utc)
        if newest.tzinfo is None:
            newest = newest.replace(tzinfo=timezone.utc)
        # REFRESH_RACE_GRACE_SECONDS bounds how long a duplicate presentation is
        # forgiven; the theft signal is a replay well after the rotation.
        return (now - newest) <= timedelta(seconds=REFRESH_RACE_GRACE_SECONDS)

    async def revoke_token(self, refresh_token: str | None) -> None:
        if not refresh_token:
            return
        token_hash = hash_secret_token(refresh_token)
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        stored = (await self.db.execute(stmt)).scalar_one_or_none()
        if stored and not stored.is_revoked:
            await self._revoke_family(stored.token_family)
            await self.db.commit()

    async def register_teacher(self, dto: TeacherRegisterRequest) -> RegisterResponse:
        if await self.repo.get_by_email(dto.email):
            # Enumeration-resistant by design: see register_student below.
            raise ResourceConflictException(self._DUPLICATE_ACCOUNT_MESSAGE)

        identifier = f"faculty-{uuid.uuid4().hex[:8]}"
        user = User(
            identifier=identifier,
            email=dto.email,
            full_name=dto.full_name,
            password_hash=await hash_password(dto.password),
            role=UserRole.TEACHER,
            is_active=False,
        )
        await self.repo.create(user)
        self.db.add(FacultyProfile(user_id=user.id, designation="Not set"))
        await self.db.commit()
        return RegisterResponse(
            message="Registered. Awaiting admin approval before you can log in.",
            requires_approval=True,
            upload_token=create_upload_token(str(user.id)),
        )

    # Deliberately identical for "email taken" and "student ID taken". A
    # distinct message turns the public signup form into a free oracle for
    # "does this person have an account here?", which for a departmental
    # portal reveals who is enrolled. The honest guidance is preserved --
    # the user is told to sign in or use password reset instead.
    _DUPLICATE_ACCOUNT_MESSAGE = (
        "An account with these details already exists. "
        "Sign in instead, or use password reset if you have forgotten it."
    )

    async def register_student(self, dto: StudentRegisterRequest) -> RegisterResponse:
        if await self.repo.get_by_email(dto.email) or await self.repo.get_by_identifier(
            dto.identifier
        ):
            raise ResourceConflictException(self._DUPLICATE_ACCOUNT_MESSAGE)

        # Enrolment is validated before the account is written. The ORM has a
        # FK to course_offerings, so an invented offering id used to be
        # accepted on SQLite (FKs off) and would have become an unhandled
        # IntegrityError -> HTTP 500 on Postgres. A typo must be a 422.
        offering_ids = [selection.course_offering_id for selection in dto.course_selections]
        if offering_ids:
            found = set(
                (
                    await self.db.execute(
                        select(CourseOffering.id).where(CourseOffering.id.in_(offering_ids))
                    )
                )
                .scalars()
                .all()
            )
            missing = [str(item) for item in offering_ids if item not in found]
            if missing:
                raise ValidationException(
                    "Unknown course offering(s): " + ", ".join(missing)
                )
            duplicates = {item for item in offering_ids if offering_ids.count(item) > 1}
            if duplicates:
                raise ValidationException("The same course offering was selected twice.")

        if dto.role == "cr":
            role = UserRole.CR
        elif dto.role == "er":
            role = UserRole.LAB_ASSISTANT
        else:
            role = UserRole.STUDENT
        user = User(
            identifier=dto.identifier,
            email=dto.email,
            full_name=dto.full_name,
            password_hash=await hash_password(dto.password),
            role=role,
            is_active=role == UserRole.STUDENT,  # CR and ER require admin approval
        )
        await self.repo.create(user)
        self.db.add(StudentProfile(
            user_id=user.id,
            session_year=dto.session_year,
            current_term=dto.current_term,
        ))
        for selection in dto.course_selections:
            self.db.add(CourseEnrollment(
                course_offering_id=selection.course_offering_id,
                student_id=user.id,
                status=selection.enrollment_type,
            ))
        await self.db.commit()
        requires_approval = role in (UserRole.CR, UserRole.LAB_ASSISTANT)
        if role == UserRole.CR:
            message = "Registered. Awaiting admin approval before you can log in as CR."
        elif role == UserRole.LAB_ASSISTANT:
            message = "Registered. Awaiting admin approval before you can log in as ER."
        else:
            message = "Registered successfully. You can log in now."
        return RegisterResponse(
            message=message,
            requires_approval=requires_approval,
            upload_token=create_upload_token(str(user.id)),
        )

    async def list_pending_approvals(self):
        return await self.repo.list_pending_approval()

    async def approve_user(self, user_id: uuid.UUID, actor_id: uuid.UUID | None = None):
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found.")
        was_active = user.is_active
        user.is_active = True
        # An approval often activates a pending account; that decision is
        # exactly the kind of thing an audit trail exists for.
        if actor_id and not was_active:
            await AuditService(self.db).record(
                action="user.approve",
                entity_type="user",
                entity_id=user.id,
                actor_id=actor_id,
                detail={"role": user.role.value},
            )
        await self.db.commit()
        return {"message": f"{user.full_name} approved.", "user_id": user.id}

    async def attach_avatar(self, user: User, file_key: str) -> None:
        """Persist a just-finalised avatar on the user row.

        Called only after the object has been measured and its magic bytes
        checked. Replacing an existing key leaves the old object in the
        bucket; cleaning that up is a later job, not this request's.
        """
        user.avatar_key = file_key
        await self.db.commit()