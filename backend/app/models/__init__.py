"""Import every model so Alembic and SQLAlchemy metadata stay complete.

The previous empty module meant `Base.metadata` only contained whatever
happened to be imported by the request path, so `alembic revision
--autogenerate` produced an empty initial schema.
"""

from app.models.academic import (  # noqa: F401
    ClassSchedule,
    Course,
    CourseEnrollment,
    CourseOffering,
    CourseOfferingTeacher,
    Semester,
)
from app.models.ai_knowledge import (  # noqa: F401
    AIChatMessage,
    AIChatSession,
    DocumentChunk,
    KnowledgeDocument,
    StudyPlan,
)
from app.models.alumni import (  # noqa: F401
    AlumniProfile,
    Event,
    EventRSVP,
    GalleryAlbum,
    GalleryPhoto,
    MentorshipPair,
    NewsPost,
    Scholarship,
    ScholarshipApplication,
)
from app.models.attendance import AttendanceRecord, AttendanceSession  # noqa: F401
from app.models.auth import PasswordResetToken, RefreshToken  # noqa: F401
from app.models.career import CareerOpportunity, StudentCVProfile, StudentPortfolio  # noqa: F401
from app.models.facility import Room, RoomReservation  # noqa: F401
from app.models.lab import (  # noqa: F401
    DamageReport,
    EquipmentAsset,
    EquipmentBorrowRequest,
    EquipmentModel,
)
from app.models.notification import Notification, NotificationPreference, UserDevice  # noqa: F401
from app.models.project import (  # noqa: F401
    Project,
    ProjectMember,
    ProjectPublication,
    SupervisorProposal,
)
from app.models.resource import AcademicResource, BookExchange  # noqa: F401
from app.models.user import FacultyProfile, StudentProfile, User, UserRole  # noqa: F401

__all__ = [
    "User",
    "UserRole",
    "StudentProfile",
    "FacultyProfile",
    "AlumniProfile",
    "Event",
    "EventRSVP",
    "Scholarship",
    "ScholarshipApplication",
    "MentorshipPair",
    "NewsPost",
    "GalleryAlbum",
    "GalleryPhoto",
]
