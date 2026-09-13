import uuid
from datetime import date, time
from sqlalchemy import String, Boolean, Numeric, Date, Time, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, UUIDPrimaryKeyMixin
# backend/app/models/academic.py
import uuid
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

class CourseOfferingTeacher(Base, UUIDPrimaryKeyMixin, TimestampMixin):
  __tablename__ = "course_offering_teachers"

  course_offering_id: Mapped[uuid.UUID] = mapped_column(
      UUID(as_uuid=True),
      ForeignKey("course_offerings.id", ondelete="CASCADE"),
      nullable=False,
      index=True,
  )
  teacher_id: Mapped[uuid.UUID] = mapped_column(
      UUID(as_uuid=True),
      ForeignKey("users.id", ondelete="CASCADE"),
      nullable=False,
      index=True,
  )
  role: Mapped[str] = mapped_column(
      String(50), default="course_teacher"
  )  # e.g., 'course_teacher', 'coordinator', 'lab_instructor'

class Semester(Base):
    __tablename__ = "semesters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

class Course(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "courses"

    course_code: Mapped[str] = mapped_column(String(12), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    credit_hours: Mapped[float] = mapped_column(Numeric(3, 1), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)

class CourseOffering(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "course_offerings"

    course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)
    semester_id: Mapped[int] = mapped_column(Integer, ForeignKey("semesters.id"), nullable=False)
    coordinator_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

class CourseEnrollment(Base):
    __tablename__ = "course_enrollments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_offering_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("course_offerings.id"), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="enrolled")
    advisor_approved: Mapped[bool] = mapped_column(Boolean, default=False)

class ClassSchedule(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "class_schedules"

    course_offering_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("course_offerings.id"), nullable=False)
    room_id: Mapped[int] = mapped_column(Integer, ForeignKey("rooms.id"), nullable=False)
    instructor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    day_of_week: Mapped[str] = mapped_column(String(15), nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

class CourseOfferingTeacher(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "course_offering_teachers"

    course_offering_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("course_offerings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(50), default="course_teacher")