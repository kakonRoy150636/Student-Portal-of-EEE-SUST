import uuid
from typing import Literal
from pydantic import BaseModel, EmailStr, Field
from app.models.user import UserRole

class LoginRequest(BaseModel):
    # Accepts either the institutional identifier (VARCHAR(32)) or the login
    # email (VARCHAR(255)), so the cap must be the wider of the two.
    identifier: str = Field(..., min_length=3, max_length=255)
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
    # Previously persisted on the model but never returned, so the client had
    # no way to build an <img src> after registering or logging in.
    avatar_key: str | None = None

    class Config:
        from_attributes = True

class AuthSessionResponse(BaseModel):
    user: UserResponse
    tokens: TokenResponse


class CourseSelection(BaseModel):
    course_offering_id: uuid.UUID
    enrollment_type: Literal["main", "drop", "improvement"] = "main"


class TeacherRegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str = Field(..., min_length=6)
    # avatar_key is deliberately absent: the only write path is
    # /auth/avatar-upload/finalize after the object has been measured.


class StudentRegisterRequest(BaseModel):
    full_name: str
    identifier: str = Field(..., min_length=3, max_length=32)
    email: EmailStr
    password: str = Field(..., min_length=6)
    session_year: str
    current_term: str
    role: Literal["student", "cr", "er"] = "student"
    course_selections: list[CourseSelection] = Field(default_factory=list)


class PendingApprovalUser(BaseModel):
    id: uuid.UUID
    full_name: str
    email: EmailStr
    identifier: str
    role: UserRole

    class Config:
        from_attributes = True


class RegisterResponse(BaseModel):
    message: str
    requires_approval: bool
    # Short-lived token the client uses only to attach a photo after the
    # account exists. Absent when the caller did not need one. Never a session.
    upload_token: str | None = None


class AvatarUploadResponse(BaseModel):
    file_key: str
    upload_url: str
    # Echo of the Content-Type pinned into the signature. The browser must
    # send this verbatim on the PUT or storage rejects the upload; the
    # client's own file.type is deliberately not consulted.
    content_type: str


class AvatarFinalizeRequest(BaseModel):
    file_key: str


class AvatarFinalizeResponse(BaseModel):
    file_key: str
    size: int
