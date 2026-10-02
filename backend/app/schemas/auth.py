import uuid
from datetime import datetime
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
    # Both drive the client: a true flag sends it to the forced-password screen,
    # the second to MFA enrolment. The server enforces the same restriction
    # independently, so a client that ignores the flag still cannot proceed.
    must_change_password: bool = False
    mfa_enabled: bool = False

    class Config:
        from_attributes = True


class AuthSessionResponse(BaseModel):
    user: UserResponse
    tokens: TokenResponse


class MfaChallengeResponse(BaseModel):
    """First step of a login that still needs a one-time code.

    Deliberately not a session: ``mfa_token`` is a 5-minute JWT scoped to
    /auth/mfa/verify and is accepted nowhere else.
    """

    mfa_required: bool = True
    mfa_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class MfaVerifyRequest(BaseModel):
    mfa_token: str = Field(..., min_length=10)
    code: str = Field(..., min_length=6, max_length=10)


class MfaSetupResponse(BaseModel):
    secret: str
    # otpauth:// URI for authenticator apps that accept one; the secret also
    # works everywhere by manual entry.
    otpauth_uri: str


class MfaEnableRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=10)


class MfaEnableResponse(BaseModel):
    message: str
    recovery_codes: list[str]


class MfaDisableRequest(BaseModel):
    password: str = Field(..., min_length=1, max_length=128)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str = Field(..., min_length=16, max_length=256)
    new_password: str = Field(..., min_length=8, max_length=128)


class SessionSummary(BaseModel):
    """One refresh-token family, i.e. one signed-in device."""

    family_id: uuid.UUID
    created_at: datetime | None = None
    last_used_at: datetime | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    is_current: bool = False
    is_active: bool = True


class CourseSelection(BaseModel):
    course_offering_id: uuid.UUID
    enrollment_type: Literal["main", "drop", "improvement"] = "main"


class TeacherRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    # 8 rather than 6: the review flagged the old floor, and every new account
    # is created through this schema or the bootstrap env (which enforces 12).
    password: str = Field(..., min_length=8, max_length=128)
    # avatar_key is deliberately absent: the only write path is
    # /auth/avatar-upload/finalize after the object has been measured.


class StudentRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    identifier: str = Field(..., min_length=3, max_length=32)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    # These are VARCHAR(9)/VARCHAR(4) in the database. Unbounded input used to
    # reach the driver, where an over-long value is a truncation error on
    # Postgres (unhandled 500) and silent corruption on SQLite.
    session_year: str = Field(..., pattern=r"^\d{2,4}(-\d{2,4})?$")
    current_term: str = Field(..., pattern=r"^\d{1,2}-\d{1,2}$")
    role: Literal["student", "cr", "er"] = "student"
    course_selections: list[CourseSelection] = Field(default_factory=list, max_length=20)


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
