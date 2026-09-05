import uuid
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

class Project(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "projects"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    abstract: Mapped[str] = mapped_column(String(1000), nullable=False)
    tier: Mapped[str] = mapped_column(String(50), default="capstone_thesis")
    semester_id: Mapped[int] = mapped_column(Integer, ForeignKey("semesters.id"), nullable=False)
    supervisor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    github_repo_url: Mapped[str] = mapped_column(String(255), nullable=True)

class ProjectMember(Base):
    __tablename__ = "project_members"

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), primary_key=True)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(30), default="member")

class SupervisorProposal(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "supervisor_proposals"

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    faculty_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    proposal_text: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")

class ProjectPublication(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "project_publications"

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    conference_name: Mapped[str] = mapped_column(String(200), nullable=True)
    doi_url: Mapped[str] = mapped_column(String(255), nullable=True)
    paper_file_key: Mapped[str] = mapped_column(String(512), nullable=False)
