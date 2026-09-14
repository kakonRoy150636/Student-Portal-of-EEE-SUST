import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.user_repository import UserRepository
from app.core.security import verify_password, get_password_hash, create_access_token, generate_random_token
from app.core.exceptions import UnauthorizedException, ResourceConflictException, NotFoundException
from app.schemas.auth import (
    LoginRequest, AuthSessionResponse, TokenResponse, UserResponse,
    TeacherRegisterRequest, StudentRegisterRequest, RegisterResponse,
)
from app.models.user import User, UserRole, StudentProfile, FacultyProfile
from app.models.academic import CourseEnrollment

class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = UserRepository(db)

    async def authenticate(self, dto: LoginRequest):
        user = await self.repo.get_by_identifier(dto.identifier)
        if not user or not verify_password(dto.password, user.password_hash):
            raise UnauthorizedException("Invalid institutional identifier or password.")
        if not user.is_active:
            if user.role in (UserRole.TEACHER, UserRole.CR):
                raise UnauthorizedException("Your account is awaiting admin approval.")
            raise UnauthorizedException("User account is inactive.")

        token = create_access_token({"sub": str(user.id), "role": user.role.value})
        refresh = generate_random_token()
        return AuthSessionResponse(user=UserResponse.model_validate(user), tokens=TokenResponse(access_token=token)), refresh

    async def register_teacher(self, dto: TeacherRegisterRequest) -> RegisterResponse:
        if await self.repo.get_by_email(dto.email):
            raise ResourceConflictException("Email already in use.")

        identifier = f"faculty-{uuid.uuid4().hex[:8]}"
        user = User(
            identifier=identifier,
            email=dto.email,
            full_name=dto.full_name,
            avatar_key=dto.avatar_key,
            password_hash=get_password_hash(dto.password),
            role=UserRole.TEACHER,
            is_active=False,
        )
        await self.repo.create(user)
        self.db.add(FacultyProfile(user_id=user.id, designation="Not set"))
        await self.db.commit()
        return RegisterResponse(
            message="Registered. Awaiting admin approval before you can log in.",
            requires_approval=True,
        )

    async def register_student(self, dto: StudentRegisterRequest) -> RegisterResponse:
        if await self.repo.get_by_email(dto.email):
            raise ResourceConflictException("Email already in use.")
        if await self.repo.get_by_identifier(dto.identifier):
            raise ResourceConflictException("Student ID already in use.")

        role = UserRole.CR if dto.role == "cr" else UserRole.STUDENT
        user = User(
            identifier=dto.identifier,
            email=dto.email,
            full_name=dto.full_name,
            avatar_key=dto.avatar_key,
            password_hash=get_password_hash(dto.password),
            role=role,
            is_active=role == UserRole.STUDENT,
        )
        await self.repo.create(user)
        self.db.add(StudentProfile(
            user_id=user.id,
            session_year=dto.session_year,
            current_term=dto.current_term,
        ))
        for selection in dto.course_selections:
            self.db.add(CourseEnrollment(
                course_offering_id=selection.course_offering_id,
                student_id=user.id,
                status=selection.enrollment_type,
            ))
        await self.db.commit()
        requires_approval = role == UserRole.CR
        return RegisterResponse(
            message=(
                "Registered. Awaiting admin approval before you can log in as CR."
                if requires_approval else "Registered successfully. You can log in now."
            ),
            requires_approval=requires_approval,
        )

    async def list_pending_approvals(self):
        return await self.repo.list_pending_approval()

    async def approve_user(self, user_id: uuid.UUID):
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found.")
        user.is_active = True
        await self.db.commit()
        return {"message": f"{user.full_name} approved.", "user_id": user.id}
