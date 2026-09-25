"""Alumni Portal endpoints: registration, verification queue, admin decisions.

Endpoints stay thin -- validate with Pydantic, delegate to AlumniService,
return a response model. No ORM access and no business rules here.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import RequireRole, get_current_user
from app.core.database import get_db
from app.models.user import User, UserRole
from app.schemas.alumni import (
    AlumniProfileCreate,
    AlumniProfileResponse,
    AlumniRegisterRequest,
    AlumniVerificationDecision,
)
from app.schemas.auth import RegisterResponse
from app.services.alumni_service import AlumniService

router = APIRouter(prefix="/alumni", tags=["Alumni"])

# Verification is an admin-only capability, mirroring the existing
# /auth/admin/pending-approvals and /auth/admin/approve/{user_id} pair.
admin_only = RequireRole([UserRole.SUPER_ADMIN])


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register_alumni(
    payload: AlumniRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new alumni account and a pending verification claim."""
    return await AlumniService(db).register(payload)


@router.get("/me", response_model=AlumniProfileResponse | None)
async def my_profile(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await AlumniService(db).get_my_profile(user)


@router.post("/claim", response_model=AlumniProfileResponse, status_code=201)
async def submit_claim(
    payload: AlumniProfileCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Attach a batch/department claim to the authenticated user's account.

    The claim is always created ``pending``; only an admin can activate it.
    """
    return await AlumniService(db).submit_claim(user, payload)


@router.get(
    "/admin/pending",
    response_model=list[AlumniProfileResponse],
)
async def pending_verifications(
    user: User = Depends(admin_only),
    db: AsyncSession = Depends(get_db),
):
    return await AlumniService(db).list_pending_verifications()


@router.patch("/admin/approve/{profile_id}", response_model=AlumniProfileResponse)
async def approve_claim(
    profile_id: uuid.UUID,
    user: User = Depends(admin_only),
    db: AsyncSession = Depends(get_db),
):
    """Approve a pending claim: membership becomes active and the account opens."""
    return await AlumniService(db).approve(profile_id, user)


@router.patch("/admin/reject/{profile_id}", response_model=AlumniProfileResponse)
async def reject_claim(
    profile_id: uuid.UUID,
    payload: AlumniVerificationDecision | None = None,
    user: User = Depends(admin_only),
    db: AsyncSession = Depends(get_db),
):
    """Reject a pending claim: membership is refused and the account stays closed."""
    return await AlumniService(db).reject(profile_id, user, payload)
