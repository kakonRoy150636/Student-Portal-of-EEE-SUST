import uuid
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.auth_service import AuthService
from app.schemas.auth import (
    AuthSessionResponse, LoginRequest, PendingApprovalUser, RegisterResponse,
    StudentRegisterRequest, TeacherRegisterRequest, UserResponse,
)
from app.api.dependencies import RequireRole, get_current_user
from app.models.user import User, UserRole

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=AuthSessionResponse)
async def login(payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    session_data, refresh_token = await service.authenticate(payload)
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, path="/api/v1/auth")
    return session_data

@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return user

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="refresh_token", path="/api/v1/auth")
    return {"message": "Logged out"}


@router.post("/register/teacher", response_model=RegisterResponse, status_code=201)
async def register_teacher(payload: TeacherRegisterRequest, db: AsyncSession = Depends(get_db)):
    return await AuthService(db).register_teacher(payload)


@router.post("/register/student", response_model=RegisterResponse, status_code=201)
async def register_student(payload: StudentRegisterRequest, db: AsyncSession = Depends(get_db)):
    return await AuthService(db).register_student(payload)


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
