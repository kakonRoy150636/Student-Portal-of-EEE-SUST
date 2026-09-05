import uuid
from pydantic import BaseModel, EmailStr
from app.models.user import UserRole

class UserUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None

class ProfileResponse(BaseModel):
    id: uuid.UUID
    identifier: str
    full_name: str
    email: EmailStr
    role: UserRole
