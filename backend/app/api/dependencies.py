import uuid
from typing import List
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User, UserRole
# backend/app/api/dependencies.py
from app.models.academic import CourseOfferingTeacher
from app.models.user import User, UserRole
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.academic import CourseOfferingTeacher

security_scheme = HTTPBearer(auto_error=True)

async def get_current_user(
    cred: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    token = cred.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token.")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Credentials invalid.")

    stmt = select(User).where(User.id == uuid.UUID(user_id))
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not active.")
    return user

class RequireRole:
    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_user)) -> User:
        if user.role not in self.allowed_roles:
            raise HTTPException(status_code=403, detail="Forbidden.")
        return user

async def verify_course_teacher(
    course_offering_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
  if user.role == UserRole.SUPER_ADMIN:
    return user

  if user.role != UserRole.TEACHER:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="Teacher role required."
    )

  stmt = select(CourseOfferingTeacher).where(
      CourseOfferingTeacher.course_offering_id == course_offering_id,
      CourseOfferingTeacher.teacher_id == user.id,
  )
  result = await db.execute(stmt)
  if not result.scalar_one_or_none():
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You are not assigned as a teacher for this course.",
    )

  return user
  