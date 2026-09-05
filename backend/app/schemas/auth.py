import uuid
from pydantic import BaseModel, EmailStr, Field
from app.models.user import UserRole

class LoginRequest(BaseModel):
    identifier: str = Field(..., min_length=3, max_length=32)
    password: str = Field(..., min_length=6)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"

class UserResponse(BaseModel):
    id: uuid.UUID
    identifier: str
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool

    class Config:
        from_attributes = True

class AuthSessionResponse(BaseModel):
    user: UserResponse
    tokens: TokenResponse
