import uuid
from typing import List
import jwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.academic import CourseOfferingTeacher

security_scheme = HTTPBearer(auto_error=True)

async def get_current_user(
    cred: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    token = cred.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Credentials invalid."
        )

    # Only access tokens are accepted here; create_access_token stamps this
    # claim and nothing else mints one, so a future refresh-token flow cannot
    # accidentally be traded for an access token.
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type."
        )

    user_id = payload.get("sub")
    # Guard the UUID cast: an unparsable sub must be a 401, not an uncaught
    # ValueError bubbling up as a 500.
    try:
        user_uuid = uuid.UUID(user_id)
    except (TypeError, ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token."
        )

    stmt = select(User).where(User.id == user_uuid)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not active."
        )
    return user


async def get_avatar_actor(
    cred: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Caller of the avatar upload/finalize routes.

    Accepts a normal access token (logged-in user changing their photo) or
    the short-lived ``avatar_upload`` token minted at registration. The
    upload token is the only way a just-created, still-pending teacher/CR/ER
    can attach a photo, because ``get_current_user`` rejects inactive
    accounts. It is not a session: it cannot call any other route.
    """
    token = cred.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Credentials invalid."
        )

    token_type = payload.get("type")
    if token_type not in ("access", "avatar_upload"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type."
        )

    try:
        user_uuid = uuid.UUID(payload.get("sub"))
    except (TypeError, ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token."
        )

    stmt = select(User).where(User.id == user_uuid)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not active."
        )
    # Access tokens still require an active account. Upload tokens do not:
    # the whole point is to let a pending account finish attaching a photo.
    if token_type == "access" and not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not active."
        )
    return user

class RequireRole:
    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_user)) -> User:
        if user.role not in self.allowed_roles:
            raise HTTPException(status_code=403, detail="Forbidden.")
        return user


def get_client_ip(request: Request) -> str:
    """Best-effort client address for throttling.

    Returns a *throttle bucket key* only. It is never an identity and never
    an authorisation input -- callers must not treat it as either.

    X-Forwarded-For is honoured **only when the request arrived over a
    trusted proxy**, because XFF is trivially attacker-controlled: sent
    directly, any client can set it to an arbitrary value and mint a fresh
    per-IP bucket per request, which would defeat the IP counter entirely
    (verified: rotating XFF produced no backoff while a fixed value did).

    TRUSTED_PROXIES is therefore an allowlist of proxy addresses that are
    permitted to *speak for* their forwarded client. With it empty -- the
    default, and correct for the current deployment where the API port is
    reached directly -- the peer address is used and XFF is ignored
    outright, so a spoofed header buys an attacker nothing.

    Set TRUSTED_PROXIES when the API is placed behind a reverse proxy (a
    real deployment must), listing the proxy's exact peer address, e.g.
    TRUSTED_PROXIES='["172.16.0.5"]'. This is an exact-string match, not
    a CIDR. Only then is the left-most XFF entry used, as recorded by
    the outermost trusted hop.
    """
    peer = request.client.host if request.client else None
    if peer and peer in settings.TRUSTED_PROXIES:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            first = forwarded.split(",")[0].strip()
            if first:
                return first
    return peer or "unknown"

async def verify_course_teacher(
    course_offering_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
  if user.role == UserRole.SUPER_ADMIN:
    return user

  if user.role != UserRole.TEACHER:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="Teacher role required."
    )

  stmt = select(CourseOfferingTeacher).where(
      CourseOfferingTeacher.course_offering_id == course_offering_id,
      CourseOfferingTeacher.teacher_id == user.id,
  )
  result = await db.execute(stmt)
  if not result.scalar_one_or_none():
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You are not assigned as a teacher for this course.",
    )

  return user
  