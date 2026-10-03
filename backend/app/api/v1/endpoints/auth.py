import uuid
import os
import re
from starlette.concurrency import run_in_threadpool
from app.core.uploads import publish_upload

import jwt
from fastapi import APIRouter, Depends, Response, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.auth_service import AuthService
from app.schemas.auth import (
    LoginRequest, AuthSessionResponse, UserResponse, TeacherRegisterRequest,
    StudentRegisterRequest, RegisterResponse, PendingApprovalUser,
    AvatarUploadResponse, AvatarFinalizeRequest, AvatarFinalizeResponse,
)
from app.api.dependencies import get_current_user, get_avatar_actor, RequireRole, get_client_ip
from app.api.request_limits import limit_login, limit_refresh, limit_registration
from app.models.user import User, UserRole
from app.core.config import settings
from app.core.exceptions import UnauthorizedException
import boto3
from botocore.exceptions import BotoCoreError, ClientError

router = APIRouter(prefix="/auth", tags=["Authentication"])

REFRESH_COOKIE = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"

# Avatars are served straight to the browser, so only formats a browser will
# actually render are accepted; the extension is derived from this allowlist
# rather than from the client-supplied filename.
ALLOWED_AVATAR_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_AVATAR_BYTES = 10 * 1024 * 1024

# Maps the client-supplied filename extension to the Content-Type we pin onto
# the stored object. Deriving the type from an allowlist (rather than echoing
# the client's content_type) is what stops a "photo.jpg" that is really an
# SVG or an HTML polyglot from being stored with an attacker-chosen type.
AVATAR_EXTENSION_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def _set_refresh_cookie(response: Response, value: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=value,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
    )


@router.post("/login", response_model=AuthSessionResponse, dependencies=[Depends(limit_login)])
async def login(
    payload: LoginRequest,
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    session_data, refresh_token = await service.authenticate(payload, get_client_ip(request))
    _set_refresh_cookie(response, refresh_token)
    return session_data


@router.post("/refresh", response_model=AuthSessionResponse, dependencies=[Depends(limit_refresh)])
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    refresh_token = request.cookies.get(REFRESH_COOKIE)
    if not refresh_token:
        raise UnauthorizedException("No refresh token provided.")
    access, new_refresh = await AuthService(db).refresh_access_token(refresh_token)
    _set_refresh_cookie(response, new_refresh)
    # Keep the shape consistent with login: user must be resolved for the response model.
    payload = jwt.decode(access, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    user = await AuthService(db).repo.get_by_id(uuid.UUID(payload["sub"]))
    from app.schemas.auth import TokenResponse
    return AuthSessionResponse(
        user=UserResponse.model_validate(user),
        tokens=TokenResponse(access_token=access),
    )


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return user


@router.post("/logout")
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    refresh_token = request.cookies.get(REFRESH_COOKIE)
    await AuthService(db).revoke_token(refresh_token)
    response.delete_cookie(key=REFRESH_COOKIE, path=REFRESH_COOKIE_PATH)
    return {"message": "Logged out"}


@router.post("/register/teacher", response_model=RegisterResponse, status_code=201, dependencies=[Depends(limit_registration)])
async def register_teacher(
    payload: TeacherRegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    # Atomic registration budget is enforced by the route dependency.
    return await AuthService(db).register_teacher(payload)


@router.post("/register/student", response_model=RegisterResponse, status_code=201, dependencies=[Depends(limit_registration)])
async def register_student(
    payload: StudentRegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    return await AuthService(db).register_student(payload)


@router.post("/avatar-upload", response_model=AvatarUploadResponse)
async def avatar_upload(
    filename: str,
    user: User = Depends(get_avatar_actor),
):
    """Issue a presigned PUT for an avatar, plus a finalize step to verify it.

    This endpoint previously took no authentication, so an anonymous caller
    could mint an unauthenticated write primitive into a publicly readable
    bucket. The client-supplied content_type is also no longer trusted.

    Size is deliberately *not* enforced here. A presigned PUT pins
    ``ContentLength`` only nominally: MinIO accepts a 500 KB body against a
    signature made for 1 byte (verified), and a bucket-policy length
    condition is rejected outright as an unsupported key. So the length is
    checked after the fact by :func:`finalize_avatar`, which asks the store
    for the object's real size, and deletes anything oversized.
    """
    # The extension is normalised and mapped to a server-side allowlist; the
    # client's own content_type is deliberately ignored. Whatever is pinned
    # here becomes the stored object's Content-Type, which is what the GET
    # response serves, so an attacker cannot negotiate their own type. MinIO
    # enforces the pinned type: a mismatched PUT is rejected with 403.
    suffix = os.path.splitext(filename)[1].lower()
    if suffix not in ALLOWED_AVATAR_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Unsupported image format.")

    content_type = AVATAR_EXTENSION_CONTENT_TYPES[suffix]
    file_key = f"avatars/{user.id}-{uuid.uuid4()}{suffix}"
    try:
        # Sign with the *public* endpoint. The internal http://minio:9000
        # hostname is only resolvable inside the compose network, so signing
        # with it handed the browser a URL it could not load.
        client = boto3.client(
            "s3",
            endpoint_url=settings.S3_PUBLIC_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
        )
        upload_url = client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.S3_BUCKET_NAME,
                "Key": file_key,
                "ContentType": content_type,
            },
            ExpiresIn=300,
        )
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(status_code=503, detail="Avatar storage is unavailable.") from exc

    return AvatarUploadResponse(
        file_key=file_key,
        upload_url=upload_url,
        content_type=content_type,
    )


@router.post("/avatar-upload/finalize", response_model=AvatarFinalizeResponse)
async def finalize_avatar(
    payload: AvatarFinalizeRequest,
    user: User = Depends(get_avatar_actor),
    db: AsyncSession = Depends(get_db),
):
    """Confirm a just-uploaded avatar is an image and is within the size cap.

    The browser cannot be trusted to have uploaded what it claimed, and the
    PUT carries no enforceable size limit, so the object is measured
    server-side. An oversized or non-image object is deleted rather than left
    sitting unvalidated in the private staging area.
    """
    # Ownership check: without it this endpoint would let any authenticated
    # user probe or delete another user's objects by guessing a key.
    if not payload.file_key.startswith("avatars/%s-" % user.id):
        raise HTTPException(status_code=403, detail="That file does not belong to you.")
    name = payload.file_key[len(f"avatars/{user.id}-"):]
    if not re.fullmatch(r"[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}\.(jpg|jpeg|png|webp|gif)", name):
        raise HTTPException(422, "Invalid avatar upload key.")
    extension = os.path.splitext(name)[1]
    client = _s3_client()
    try:
        published_key, stored_size = await run_in_threadpool(
            publish_upload, client, payload.file_key, extension,
            AVATAR_EXTENSION_CONTENT_TYPES[extension], MAX_AVATAR_BYTES,
            f"avatars/{user.id}-",
        )
    except ValueError as exc:
        await run_in_threadpool(_delete_quietly, client, payload.file_key)
        raise HTTPException(415, str(exc)) from exc
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(503, "Avatar storage is unavailable.") from exc
    await AuthService(db).attach_avatar(user, published_key)
    await run_in_threadpool(_delete_quietly, client, payload.file_key)
    return AvatarFinalizeResponse(file_key=published_key, size=stored_size)


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
    )


def _delete_quietly(client, file_key: str) -> None:
    try:
        client.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=file_key)
    except (BotoCoreError, ClientError):
        return


@router.get("/admin/pending-approvals", response_model=list[PendingApprovalUser])
async def pending_approvals(
    user: User = Depends(RequireRole([UserRole.SUPER_ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    return await AuthService(db).list_pending_approvals()


@router.patch("/admin/approve/{user_id}")
async def approve_user(
    user_id: uuid.UUID,
    user: User = Depends(RequireRole([UserRole.SUPER_ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    return await AuthService(db).approve_user(user_id)
