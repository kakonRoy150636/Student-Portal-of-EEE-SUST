import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.user_repository import UserRepository
from app.core.security import (
    verify_password, get_password_hash, create_access_token, generate_random_token,
    hash_secret_token,
)
from app.core.config import settings
from app.core.exceptions import UnauthorizedException, ResourceConflictException, NotFoundException
from app.schemas.auth import (
    LoginRequest, AuthSessionResponse, TokenResponse, UserResponse,
    TeacherRegisterRequest, StudentRegisterRequest, RegisterResponse,
)
from app.models.user import User, UserRole, StudentProfile, FacultyProfile
from app.models.auth import RefreshToken
from app.models.academic import CourseEnrollment


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


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = UserRepository(db)

    async def _issue_refresh_token(self, user_id: uuid.UUID, family: uuid.UUID | None = None) -> str:
        """Persist a hashed refresh token and return the plaintext one.

        If ``family`` is None a new token family is started; otherwise the new
        token joins the existing family (rotation).
        """
        token = generate_random_token()
        await self.db.execute(
            RefreshToken.__table__.insert().values(
                user_id=user_id,
                token_family=family or uuid.uuid4(),
                token_hash=hash_secret_token(token),
                is_revoked=False,
                expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
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

    async def authenticate(self, dto: LoginRequest):
        user = await self.repo.get_by_identifier(dto.identifier)
        if not user or not verify_password(dto.password, user.password_hash):
            raise UnauthorizedException("Invalid institutional identifier or password.")
        if not user.is_active:
            if user.role in (UserRole.TEACHER, UserRole.CR, UserRole.LAB_ASSISTANT):
                raise UnauthorizedException("Your account is awaiting admin approval.")
            raise UnauthorizedException("User account is inactive.")

        token = create_access_token({"sub": str(user.id), "role": user.role.value})
        refresh = await self._issue_refresh_token(user.id)
        await self.db.commit()
        return AuthSessionResponse(
            user=UserResponse.model_validate(user),
            tokens=TokenResponse(access_token=token),
        ), refresh

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
            # A revoked token being presented again means the family was already
            # rotated — treat as theft: kill the whole family.
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
            raise ResourceConflictException("Email already in use.")

        identifier = f"faculty-{uuid.uuid4().hex[:8]}"
        user = User(
            identifier=identifier,
            email=dto.email,
            full_name=dto.full_name,
            avatar_key=dto.avatar_key,
            password_hash=get_password_hash(dto.password),
            role=UserRole.TEACHER,
            is_active=False,
        )
        await self.repo.create(user)
        self.db.add(FacultyProfile(user_id=user.id, designation="Not set"))
        await self.db.commit()
        return RegisterResponse(
            message="Registered. Awaiting admin approval before you can log in.",
            requires_approval=True,
        )

    async def register_student(self, dto: StudentRegisterRequest) -> RegisterResponse:
        if await self.repo.get_by_email(dto.email):
            raise ResourceConflictException("Email already in use.")
        if await self.repo.get_by_identifier(dto.identifier):
            raise ResourceConflictException("Student ID already in use.")

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
            avatar_key=dto.avatar_key,
            password_hash=get_password_hash(dto.password),
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
        )

    async def list_pending_approvals(self):
        return await self.repo.list_pending_approval()

    async def approve_user(self, user_id: uuid.UUID):
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found.")
        user.is_active = True
        await self.db.commit()
        return {"message": f"{user.full_name} approved.", "user_id": user.id}