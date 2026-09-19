import uuid
import jwt
from fastapi import APIRouter, Depends, Response, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.auth_service import AuthService
from app.schemas.auth import (
    LoginRequest, AuthSessionResponse, UserResponse, TeacherRegisterRequest,
    StudentRegisterRequest, RegisterResponse, PendingApprovalUser,
    AvatarUploadResponse,
)
from app.api.dependencies import get_current_user, RequireRole
from app.models.user import User, UserRole
from app.core.config import settings
from app.core.exceptions import UnauthorizedException
import boto3
from botocore.exceptions import BotoCoreError, ClientError

router = APIRouter(prefix="/auth", tags=["Authentication"])

REFRESH_COOKIE = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"


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
async def login(payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    session_data, refresh_token = await service.authenticate(payload)
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
async def avatar_upload(filename: str, content_type: str, size_hint: int = 5 * 1024 * 1024):
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Only image uploads are supported.")
    if size_hint > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Avatar exceeds maximum size (10 MB).")
    file_key = f"avatars/{uuid.uuid4()}-{filename.replace('/', '_')}"
    try:
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
                "ContentLengthRange": (0, size_hint),
            },
            ExpiresIn=300,
        )
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(status_code=503, detail="Avatar storage is unavailable.") from exc
    return AvatarUploadResponse(file_key=file_key, upload_url=upload_url)


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