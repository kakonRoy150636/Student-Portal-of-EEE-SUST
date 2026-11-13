import ipaddress
import uuid
from typing import List
import jwt
from redis.exceptions import RedisError
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import _get_redis
from app.models.user import User, UserRole
from app.models.academic import (
    CourseOfferingTeacher,
    CourseOffering,
    TeacherAssignmentRequest,
    TeacherAssignmentRequestStatus,
)

security_scheme = HTTPBearer(auto_error=True)
ACCESS_TOKEN_TYPE = "access"

async def get_access_token_payload(
    cred: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> dict:
    token = cred.credentials
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Credentials invalid."
        )
    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type."
        )
    jti = payload.get("jti")
    if not isinstance(jti, str):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")
    try:
        revoked = await _get_redis().get(f"auth:revoked:{jti}")
    except (RedisError, OSError):
        if settings.is_production:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Token service unavailable.")
        revoked = None
    if revoked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked.")
    return payload


async def get_current_user(
    payload: dict = Depends(get_access_token_payload),
    db: AsyncSession = Depends(get_db),
) -> User:

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
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Credentials invalid."
        )

    token_type = payload.get("type")
    if token_type not in (ACCESS_TOKEN_TYPE, "avatar_upload"):
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
    if token_type == ACCESS_TOKEN_TYPE and not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not active."
        )
    return user


def verify_browser_auth_request(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin and origin not in settings.CORS_ORIGINS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Origin not allowed.")
    fetch_site = request.headers.get("sec-fetch-site")
    if fetch_site and fetch_site not in {"same-origin", "same-site"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-site request rejected.")

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

    TRUSTED_PROXIES is therefore an allowlist of proxy addresses or CIDRs that
    are permitted to *speak for* their forwarded client. With it empty -- the
    default, and correct for the current deployment where the API port is
    reached directly -- the peer address is used and XFF is ignored
    outright, so a spoofed header buys an attacker nothing.

    Set TRUSTED_PROXIES when the API is placed behind a reverse proxy (a real
    deployment must), listing the proxy's exact peer address or a narrowly
    scoped CIDR, e.g. TRUSTED_PROXIES='["172.16.0.5"]'. Only then is the
    left-most XFF entry used, as recorded by the outermost trusted hop.
    """
    peer = request.client.host if request.client else None
    if peer and _is_trusted_proxy(peer):
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            first = forwarded.split(",")[0].strip()
            if first:
                return first
    return peer or "unknown"


def _is_trusted_proxy(peer: str) -> bool:
    """Return whether a peer matches the configured proxy allowlist."""

    try:
        peer_ip = ipaddress.ip_address(peer)
    except ValueError:
        return False
    for configured in settings.TRUSTED_PROXIES:
        try:
            if "/" in configured:
                if peer_ip in ipaddress.ip_network(configured, strict=False):
                    return True
            elif peer_ip == ipaddress.ip_address(configured):
                return True
        except ValueError:
            # A malformed allowlist entry must not accidentally trust a peer.
            continue
    return False

async def verify_course_teacher(
    course_offering_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
  if await db.scalar(select(CourseOffering.id).where(CourseOffering.id == course_offering_id)) is None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course offering not found.")

  if user.role == UserRole.SUPER_ADMIN:
    return user

  if user.role != UserRole.TEACHER:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="Teacher role required."
    )

  # A provider/creator is a valid course teacher even if a legacy database has
  # not yet materialised the assignment row.  Approved requests remain valid
  # independently, while a rejected request cannot use a stale assignment.
  stmt = (
      select(CourseOfferingTeacher)
      .join(CourseOffering, CourseOffering.id == CourseOfferingTeacher.course_offering_id)
      .outerjoin(
          TeacherAssignmentRequest,
          and_(
              TeacherAssignmentRequest.course_offering_id
              == CourseOfferingTeacher.course_offering_id,
              TeacherAssignmentRequest.teacher_id == CourseOfferingTeacher.teacher_id,
          ),
      )
      .where(
          CourseOfferingTeacher.course_offering_id == course_offering_id,
          CourseOfferingTeacher.teacher_id == user.id,
          or_(
              TeacherAssignmentRequest.id.is_(None),
              TeacherAssignmentRequest.status == TeacherAssignmentRequestStatus.APPROVED.value,
              CourseOffering.created_by == user.id,
          ),
      )
  )
  result = await db.execute(stmt)
  if result.scalar_one_or_none():
    return user

  approved_request = await db.scalar(
      select(TeacherAssignmentRequest.id).where(
          TeacherAssignmentRequest.course_offering_id == course_offering_id,
          TeacherAssignmentRequest.teacher_id == user.id,
          TeacherAssignmentRequest.status == TeacherAssignmentRequestStatus.APPROVED.value,
      )
  )
  provider = await db.scalar(
      select(CourseOffering.id).where(
          CourseOffering.id == course_offering_id,
          CourseOffering.created_by == user.id,
      )
  )
  if approved_request is None and provider is None:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You are not assigned as a teacher for this course.",
    )

  return user
