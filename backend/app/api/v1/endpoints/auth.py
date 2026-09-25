import uuid
import os

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


@router.post("/login", response_model=AuthSessionResponse)
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


@router.post("/refresh", response_model=AuthSessionResponse)
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


@router.post("/register/teacher", response_model=RegisterResponse, status_code=201)
async def register_teacher(payload: TeacherRegisterRequest, db: AsyncSession = Depends(get_db)):
    return await AuthService(db).register_teacher(payload)


@router.post("/register/student", response_model=RegisterResponse, status_code=201)
async def register_student(payload: StudentRegisterRequest, db: AsyncSession = Depends(get_db)):
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
    sitting in a publicly readable bucket.
    """
    # Ownership check: without it this endpoint would let any authenticated
    # user probe or delete another user's objects by guessing a key.
    if not payload.file_key.startswith("avatars/%s-" % user.id):
        raise HTTPException(status_code=403, detail="That file does not belong to you.")

    try:
        client = _s3_client()
        head = client.head_object(Bucket=settings.S3_BUCKET_NAME, Key=payload.file_key)
    except ClientError as exc:
        code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if code == 404:
            raise HTTPException(status_code=404, detail="Upload not found. Please try again.") from exc
        raise HTTPException(status_code=503, detail="Avatar storage is unavailable.") from exc

    stored_size = int(head.get("ContentLength", 0))
    stored_type = (head.get("ContentType") or "").lower()

    if stored_size < 1 or stored_size > MAX_AVATAR_BYTES:
        _delete_quietly(client, payload.file_key)
        raise HTTPException(
            status_code=413,
            detail="That image is larger than the 10 MB limit and was not saved.",
        )

    if stored_type not in AVATAR_EXTENSION_CONTENT_TYPES.values() or not _has_image_magic(
        stored_type, payload.file_key, client
    ):
        _delete_quietly(client, payload.file_key)
        raise HTTPException(status_code=415, detail="That file is not a valid image.")

    # Stamp Content-Disposition on the stored object. MinIO serves this on
    # anonymous GET, which is the only header we can actually control without
    # putting nginx in front of the bucket. X-Content-Type-Options: nosniff
    # cannot be set this way -- that still needs a proxy, tracked separately.
    try:
        client.copy_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=payload.file_key,
            CopySource={"Bucket": settings.S3_BUCKET_NAME, "Key": payload.file_key},
            ContentType=stored_type,
            ContentDisposition="inline",
            MetadataDirective="REPLACE",
        )
    except (BotoCoreError, ClientError):
        # The object is already a measured image; a metadata stamp failure
        # must not undo a successful upload.
        pass

    # Persist only after the object has been measured. Register used to
    # accept a client-supplied avatar_key, which let anyone point their
    # account at another user's object (or at a key that was never uploaded).
    await AuthService(db).attach_avatar(user, payload.file_key)
    return AvatarFinalizeResponse(file_key=payload.file_key, size=stored_size)


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


# Leading-byte signatures, checked against the first 12 bytes of the object.
#
# Best-effort sanity check: it rejects empty, corrupt, or non-image blobs that
# the client mislabelled. It is NOT a polyglot/XSS defence. A crafted file can
# pass this while still carrying an executable payload *after* the magic bytes
# -- a GIF89a+JS polyglot, for example, has a perfectly valid 6-byte header
# and then carries script after it, so this check passes. The real mitigations
# are the server-pinned Content-Type (so the stored object's type is never
# attacker-chosen) plus nosniff/Content-Disposition on serve. Full byte-level
# verification would mean decoding the image (e.g. Pillow), which is
# disproportionate for an MVP avatar field.
#
# Served directly from MinIO, so nosniff cannot be set per-object without an
# nginx S3-proxy route in front of it -- tracked separately, not done here.
_IMAGE_MAGIC = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/gif": (b"GIF87a", b"GIF89a"),
    "image/webp": (b"RIFF",),
}


def _has_image_magic(content_type: str, file_key: str, client) -> bool:
    prefixes = _IMAGE_MAGIC.get(content_type)
    if not prefixes:
        # Allowed type we have no signature for: do not reject on bytes alone.
        return True
    try:
        chunk = client.get_object(
            Bucket=settings.S3_BUCKET_NAME, Key=file_key, Range="bytes=0-11"
        )["Body"].read()
    except (BotoCoreError, ClientError):
        return False
    return any(chunk.startswith(p) for p in prefixes)


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