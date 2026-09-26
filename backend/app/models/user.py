from __future__ import annotations

import enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Boolean, Enum, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.alumni import AlumniProfile

class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    TEACHER = "teacher"
    CR = "cr"
    STUDENT = "student"
    LAB_ASSISTANT = "lab_assistant"
    ALUMNI = "alumni"

class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    identifier: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    avatar_key: Mapped[Optional[str]] = mapped_column(String(512))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=lambda roles: [role.value for role in roles]),
        default=UserRole.STUDENT,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    student_profile: Mapped[Optional["StudentProfile"]] = relationship("StudentProfile", back_populates="user", uselist=False)
    faculty_profile: Mapped[Optional["FacultyProfile"]] = relationship("FacultyProfile", back_populates="user", uselist=False)
    alumni_profile: Mapped[Optional["AlumniProfile"]] = relationship("AlumniProfile", back_populates="user", uselist=False)

class StudentProfile(Base):
    __tablename__ = "profiles_student"

    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    session_year: Mapped[str] = mapped_column(String(9), nullable=False)
    current_term: Mapped[str] = mapped_column(String(4), nullable=False)
    blood_group: Mapped[Optional[str]] = mapped_column(String(3))
    contact_number: Mapped[Optional[str]] = mapped_column(String(20))
    github_profile: Mapped[Optional[str]] = mapped_column(String(255))
    linkedin_profile: Mapped[Optional[str]] = mapped_column(String(255))

    user: Mapped["User"] = relationship("User", back_populates="student_profile")

class FacultyProfile(Base):
    __tablename__ = "profiles_faculty"

    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    designation: Mapped[str] = mapped_column(String(100), nullable=False)
    room_number: Mapped[Optional[str]] = mapped_column(String(50))
    office_hours: Mapped[Optional[str]] = mapped_column(String(255))
    research_areas: Mapped[Optional[list]] = mapped_column(ARRAY(String(200)))

    user: Mapped["User"] = relationship("User", back_populates="faculty_profile")
