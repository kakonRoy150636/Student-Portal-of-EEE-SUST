import uuid
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field
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
    avatar_key: str | None = None

    model_config = ConfigDict(from_attributes=True)

class AuthSessionResponse(BaseModel):
    user: UserResponse
    tokens: TokenResponse


class CourseSelection(BaseModel):
    course_offering_id: uuid.UUID
    enrollment_type: Literal["main", "drop", "improvement"] = "main"


class TeacherRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(..., min_length=6)
    avatar_key: str | None = None


class StudentRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    identifier: str = Field(..., min_length=3, max_length=32)
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: Literal["student", "cr"] = "student"
    session_year: str = Field(..., min_length=1, max_length=9)
    current_term: str = Field(..., min_length=1, max_length=4)
    avatar_key: str | None = None
    course_selections: list[CourseSelection] = Field(default_factory=list)


class PendingApprovalUser(BaseModel):
    id: uuid.UUID
    full_name: str
    email: EmailStr
    identifier: str
    role: UserRole

    model_config = ConfigDict(from_attributes=True)


class RegisterResponse(BaseModel):
    message: str
    requires_approval: bool
