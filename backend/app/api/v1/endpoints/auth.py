from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.auth_service import AuthService
from app.schemas.auth import LoginRequest, AuthSessionResponse, UserResponse
from app.api.dependencies import get_current_user
from app.models.user import User

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
