import enum
import uuid
from datetime import date, datetime, time, timezone
from decimal import Decimal

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Date, DateTime, Enum as SAEnum, ForeignKey, Index,
    Integer, Numeric, SQLColumnExpression, String, Time, UniqueConstraint, func, select, text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class OfferingPublicationStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"


class TeacherAssignmentRequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class EnrollmentStatus(str, enum.Enum):
    ENROLLED = "enrolled"
    MAIN = "main"
    IMPROVEMENT = "improvement"
    DROP = "drop"


ACTIVE_ENROLLMENT_STATUSES = (
    EnrollmentStatus.ENROLLED.value, EnrollmentStatus.MAIN.value, EnrollmentStatus.IMPROVEMENT.value,
)


class CourseOfferingTeacher(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "course_offering_teachers"
    __table_args__ = (
        UniqueConstraint(
            "course_offering_id", "teacher_id", name="course_offering_teachers_course_offering_id_teacher_id_key",
        ),
    )

    course_offering_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("course_offerings.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    role: Mapped[str] = mapped_column(
        String(50), default="course_teacher", server_default="course_teacher", nullable=False,
    )  # e.g., 'course_teacher', 'coordinator', 'lab_instructor'


class Semester(Base):
    __tablename__ = "semesters"
    __table_args__ = (
        CheckConstraint(
            "target_term IS NULL OR target_term IN "
            "('1-1', '1-2', '2-1', '2-2', '3-1', '3-2', '4-1', '4-2')",
            name="ck_semesters_target_term",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    target_term: Mapped[str | None] = mapped_column(String(4), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)


class Course(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "courses"

    course_code: Mapped[str] = mapped_column(String(12), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    credit_hours: Mapped[Decimal] = mapped_column(Numeric(3, 1), nullable=False)
    # PostgreSQL stores the catalogue type as the existing course_type enum;
    # mapping it as VARCHAR works in SQLite tests but fails on real inserts.
    type: Mapped[str] = mapped_column(
        SAEnum("theory", "lab", "thesis", "project", name="course_type"), nullable=False,
    )
    description: Mapped[str] = mapped_column(String(500), nullable=True)


class CourseOffering(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "course_offerings"
    __table_args__ = (
        UniqueConstraint("course_id", "semester_id", name="course_offerings_course_id_semester_id_key"),
        CheckConstraint(
            "publication_status IN ('draft', 'published')", name="ck_course_offerings_publication_status",
        ),
        Index("ix_course_offerings_semester_publication", "semester_id", "publication_status"),
    )

    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="RESTRICT"), nullable=False,
    )
    semester_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("semesters.id", ondelete="CASCADE"), nullable=False,
    )
    coordinator_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
    )
    # Legacy offerings have no recorded creator. Admin creation must supply
    # its authenticated actor; a coordinator is not the offering's owner.
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
    )
    publication_status: Mapped[str] = mapped_column(
        String(20), default=OfferingPublicationStatus.DRAFT.value, server_default="draft", nullable=False,
    )
    published_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )

    course: Mapped[Course] = relationship(lazy="selectin")

    @hybrid_property
    def credit_hours(self) -> Decimal:
        """Read-only catalogue credits; an offering never stores a copy."""
        return self.course.credit_hours

    @credit_hours.inplace.expression
    @classmethod
    def _credit_hours_expression(cls) -> SQLColumnExpression[Decimal]:
        return select(Course.credit_hours).where(Course.id == cls.course_id).correlate_except(Course).scalar_subquery()


class TeacherAssignmentRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "teacher_assignment_requests"
    __table_args__ = (
        UniqueConstraint("course_offering_id", "teacher_id", name="uq_teacher_assignment_requests_offering_teacher"),
        CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="ck_teacher_assignment_requests_status"),
        Index("ix_teacher_assignment_requests_status_created", "status", "created_at"),
        Index("ix_teacher_assignment_requests_teacher", "teacher_id"),
    )

    course_offering_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("course_offerings.id", ondelete="CASCADE"), nullable=False,
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20), default=TeacherAssignmentRequestStatus.PENDING.value, server_default="pending", nullable=False,
    )
    decided_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )


class CourseEnrollment(Base):
    __tablename__ = "course_enrollments"
    __table_args__ = (
        # Keep one row even after a drop; reselection updates that row.
        UniqueConstraint("course_offering_id", "student_id", name="course_enrollments_course_offering_id_student_id_key"),
        CheckConstraint("status IN ('enrolled', 'main', 'improvement', 'drop')", name="ck_course_enrollments_status"),
        Index("ix_course_enrollments_student_status", "student_id", "status"),
        Index(
            "ix_course_enrollments_notification_recipients", "course_offering_id", "student_id",
            postgresql_where=text("status IN ('enrolled', 'main', 'improvement')"),
            sqlite_where=text("status IN ('enrolled', 'main', 'improvement')"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    course_offering_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("course_offerings.id", ondelete="CASCADE"), nullable=False,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20), default=EnrollmentStatus.ENROLLED.value, server_default="enrolled", nullable=False,
    )
    # Retain the legacy column for compatibility; it does not govern enrollment.
    advisor_approved: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False,
    )
    dropped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    offering: Mapped[CourseOffering] = relationship(lazy="selectin")

    @hybrid_property
    def credit_hours(self) -> Decimal:
        """Read-only source credits, never accepted from enrollment input."""
        return self.offering.course.credit_hours

    @credit_hours.inplace.expression
    @classmethod
    def _credit_hours_expression(cls) -> SQLColumnExpression[Decimal]:
        return (
            select(Course.credit_hours)
            .join(CourseOffering, CourseOffering.course_id == Course.id)
            .where(CourseOffering.id == cls.course_offering_id)
            .correlate_except(Course, CourseOffering)
            .scalar_subquery()
        )

    @hybrid_property
    def is_active(self) -> bool:
        return self.status in ACTIVE_ENROLLMENT_STATUSES

    @is_active.inplace.expression
    @classmethod
    def _is_active_expression(cls) -> SQLColumnExpression[bool]:
        return cls.status.in_(ACTIVE_ENROLLMENT_STATUSES)

    def drop(self) -> None:
        if self.status != EnrollmentStatus.DROP.value:
            self.status = EnrollmentStatus.DROP.value
            self.dropped_at = self.updated_at = datetime.now(timezone.utc)

    def reselect(self, status: str = EnrollmentStatus.ENROLLED.value) -> None:
        """Reactivate this row, preserving its ID and original enrollment time."""
        if status not in ACTIVE_ENROLLMENT_STATUSES:
            raise ValueError("Reselection requires enrolled, main or improvement status.")
        if self.status != status:
            self.status = status
            self.dropped_at = None
            self.updated_at = datetime.now(timezone.utc)


class ClassSchedule(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "class_schedules"

    course_offering_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("course_offerings.id"), nullable=False)
    room_id: Mapped[int] = mapped_column(Integer, ForeignKey("rooms.id"), nullable=False)
    instructor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    day_of_week: Mapped[str] = mapped_column(String(15), nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
