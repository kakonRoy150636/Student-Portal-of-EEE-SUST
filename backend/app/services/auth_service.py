from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.user_repository import UserRepository
from app.core.security import verify_password, create_access_token, generate_random_token
from app.core.exceptions import UnauthorizedException
from app.schemas.auth import LoginRequest, AuthSessionResponse, TokenResponse, UserResponse

class AuthService:
    def __init__(self, db: AsyncSession):
        self.repo = UserRepository(db)

    async def authenticate(self, dto: LoginRequest):
        user = await self.repo.get_by_identifier(dto.identifier)
        if not user or not verify_password(dto.password, user.password_hash):
            raise UnauthorizedException("Invalid institutional identifier or password.")
        if not user.is_active:
            raise UnauthorizedException("User account is inactive.")

        token = create_access_token({"sub": str(user.id), "role": user.role.value})
        refresh = generate_random_token()
        return AuthSessionResponse(user=UserResponse.model_validate(user), tokens=TokenResponse(access_token=token)), refresh
