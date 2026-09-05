import uuid
from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

class KnowledgeDocument(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "knowledge_documents"

    course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)

class DocumentChunk(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "document_chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("knowledge_documents.id"), nullable=False)
    content: Mapped[str] = mapped_column(String(2000), nullable=False)

class AIChatSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "ai_chat_sessions"

    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    session_title: Mapped[str] = mapped_column(String(150), default="Course Inquiries")

class AIChatMessage(Base, TimestampMixin):
    __tablename__ = "ai_chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ai_chat_sessions.id"), nullable=False)
    sender: Mapped[str] = mapped_column(String(10), nullable=False)
    content: Mapped[str] = mapped_column(String(2000), nullable=False)

class StudyPlan(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "ai_generated_study_plans"

    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    plan_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
