"""Alumni Portal endpoints: public landing plus authenticated members' area.

Endpoints stay thin -- validate with Pydantic, delegate to AlumniService,
return a response model. No ORM access and no business rules here.
"""
import uuid

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import RequireRole, get_current_user
from app.core.database import get_db
from app.models.user import User, UserRole
from app.schemas.alumni import (
    AlumniDashboardResponse,
    AlumniDirectoryResponse,
    AlumniEmploymentInput,
    AlumniEmploymentResponse,
    AlumniImportPreviewResponse,
    AlumniImportResponse,
    AlumniBatchResponse,
    AlumniBatchSummaryResponse,
    AlumniProfileDetailResponse,
    AlumniLandingResponse,
    AlumniProfileCreate,
    AlumniProfileResponse,
    AlumniProfileUpdate,
    AlumniRegisterRequest,
    AlumniVerificationDecision,
    EventCreate,
    EventResponse,
    EventRsvpRequest,
    EventRsvpResponse,
    GalleryAlbumResponse,
    MentorshipPairResponse,
    MentorshipRequest,
    MentorshipRespondRequest,
    NewsPostResponse,
    ScholarshipApplyRequest,
    ScholarshipApplicationResponse,
    ScholarshipCreate,
    ScholarshipResponse,
    ScholarshipReviewRequest,
)
from app.schemas.auth import RegisterResponse
from app.services.alumni_service import AlumniService
from app.api.request_limits import limit_alumni_search, limit_registration

router = APIRouter(prefix="/alumni", tags=["Alumni"])

admin_only = RequireRole([UserRole.SUPER_ADMIN])
alumni_or_admin = RequireRole([UserRole.ALUMNI, UserRole.SUPER_ADMIN])


@router.post("/register", response_model=RegisterResponse, status_code=201, dependencies=[Depends(limit_registration)])
async def register_alumni(
    payload: AlumniRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new alumni account and a pending verification claim."""
    return await AlumniService(db).register(payload)


@router.get("/landing", response_model=AlumniLandingResponse)
async def alumni_landing(db: AsyncSession = Depends(get_db)):
    """Public landing page: live stats plus published news, events, gallery."""
    return await AlumniService(db).landing()


@router.get("/batches", response_model=list[AlumniBatchResponse])
async def alumni_batches(db: AsyncSession = Depends(get_db)):
    return await AlumniService(db).list_batches()


@router.get("/batches/{year}/summary", response_model=AlumniBatchSummaryResponse)
async def alumni_batch_summary(
    year: int = Query(..., ge=2010), db: AsyncSession = Depends(get_db),
):
    return await AlumniService(db).batch_summary(year)


@router.get("/", response_model=AlumniDirectoryResponse, dependencies=[Depends(limit_alumni_search)])
async def alumni_directory(
    batch: int | None = Query(default=None, ge=2010),
    company: str | None = Query(default=None, max_length=120),
    country: str | None = Query(default=None, max_length=120),
    sector: str | None = Query(default=None, pattern=r"^(industry|academia|government|startup|higher_study|other)$"),
    q: str | None = Query(default=None, min_length=1, max_length=120),
    page: int = Query(default=1, ge=1, le=100000),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    return await AlumniService(db).directory_page(
        user, batch=batch, company=company, country=country, sector=sector, q=q,
        page=page, page_size=page_size,
    )


@router.get("/directory", response_model=list[AlumniProfileResponse])
async def search_directory(
    q: str | None = Query(default=None, min_length=1, max_length=120),
    batch_year: int | None = Query(default=None, ge=1960, le=2100),
    industry: str | None = Query(default=None, max_length=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Visible, verified alumni only. Hidden or pending claims never leak."""
    return await AlumniService(db).search_directory(q=q, batch_year=batch_year, industry=industry)


@router.get("/directory/{profile_id}", response_model=AlumniProfileResponse)
async def get_directory_profile(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await AlumniService(db).get_directory_profile(profile_id)


@router.get("/me", response_model=AlumniProfileResponse | None)
async def my_profile(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await AlumniService(db).get_my_profile(user)


@router.get("/me/employments", response_model=list[AlumniEmploymentResponse])
async def my_employments(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await AlumniService(db).my_employments(user)


@router.put("/me/employments", response_model=list[AlumniEmploymentResponse])
async def replace_my_employments(
    payload: list[AlumniEmploymentInput], user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    return await AlumniService(db).update_my_employments(user, payload)


@router.patch("/me", response_model=AlumniProfileResponse)
async def update_my_profile(
    payload: AlumniProfileUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await AlumniService(db).update_my_profile(user, payload)


@router.get("/dashboard", response_model=AlumniDashboardResponse)
async def my_dashboard(user: User = Depends(alumni_or_admin), db: AsyncSession = Depends(get_db)):
    return await AlumniService(db).dashboard(user)


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


@router.get("/events", response_model=list[EventResponse])
async def list_events(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await AlumniService(db).list_events(user)


@router.get("/events/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await AlumniService(db).get_event(event_id, user)


@router.post("/events", response_model=EventResponse, status_code=201)
async def create_event(
    payload: EventCreate,
    user: User = Depends(admin_only),
    db: AsyncSession = Depends(get_db),
):
    return await AlumniService(db).create_event(user, payload)


@router.post("/events/{event_id}/rsvp", response_model=EventRsvpResponse)
async def rsvp_event(
    event_id: uuid.UUID,
    payload: EventRsvpRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await AlumniService(db).rsvp_event(user, event_id, payload)


@router.get("/scholarships", response_model=list[ScholarshipResponse])
async def list_scholarships(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await AlumniService(db).list_scholarships(user)


@router.post("/scholarships", response_model=ScholarshipResponse, status_code=201)
async def create_scholarship(
    payload: ScholarshipCreate,
    user: User = Depends(admin_only),
    db: AsyncSession = Depends(get_db),
):
    return await AlumniService(db).create_scholarship(user, payload)


@router.post(
    "/scholarships/{scholarship_id}/apply",
    response_model=ScholarshipApplicationResponse,
    status_code=201,
)
async def apply_scholarship(
    scholarship_id: uuid.UUID,
    payload: ScholarshipApplyRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await AlumniService(db).apply_scholarship(user, scholarship_id, payload)


@router.patch(
    "/scholarships/applications/{application_id}",
    response_model=ScholarshipApplicationResponse,
)
async def review_application(
    application_id: uuid.UUID,
    payload: ScholarshipReviewRequest,
    user: User = Depends(admin_only),
    db: AsyncSession = Depends(get_db),
):
    return await AlumniService(db).review_application(user, application_id, payload)


@router.get("/mentors", response_model=list[AlumniProfileResponse])
async def list_mentors(
    user: User = Depends(alumni_or_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AlumniService(db).list_mentors(user)


@router.post("/mentorship", response_model=MentorshipPairResponse, status_code=201)
async def request_mentorship(
    payload: MentorshipRequest,
    user: User = Depends(alumni_or_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AlumniService(db).request_mentorship(user, payload)


@router.patch("/mentorship/{pair_id}/accept", response_model=MentorshipPairResponse)
async def accept_mentorship(
    pair_id: uuid.UUID,
    payload: MentorshipRespondRequest | None = None,
    user: User = Depends(alumni_or_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AlumniService(db).respond_mentorship(user, pair_id, True, payload)


@router.patch("/mentorship/{pair_id}/decline", response_model=MentorshipPairResponse)
async def decline_mentorship(
    pair_id: uuid.UUID,
    payload: MentorshipRespondRequest | None = None,
    user: User = Depends(alumni_or_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AlumniService(db).respond_mentorship(user, pair_id, False, payload)


@router.get("/news", response_model=list[NewsPostResponse])
async def list_news(db: AsyncSession = Depends(get_db)):
    return await AlumniService(db).list_news()


@router.get("/news/{slug}", response_model=NewsPostResponse)
async def get_news(slug: str, db: AsyncSession = Depends(get_db)):
    return await AlumniService(db).get_news(slug)


@router.get("/gallery", response_model=list[GalleryAlbumResponse])
async def list_gallery(db: AsyncSession = Depends(get_db)):
    return await AlumniService(db).list_gallery()


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


@router.patch("/admin/{profile_id}/verify", response_model=AlumniProfileResponse)
async def verify_alumni_profile(
    profile_id: uuid.UUID, user: User = Depends(admin_only), db: AsyncSession = Depends(get_db),
):
    return await AlumniService(db).approve(profile_id, user)


@router.patch("/admin/{profile_id}/reject", response_model=AlumniProfileResponse)
async def reject_alumni_profile(
    profile_id: uuid.UUID, payload: AlumniVerificationDecision | None = None,
    user: User = Depends(admin_only), db: AsyncSession = Depends(get_db),
):
    return await AlumniService(db).reject(profile_id, user, payload)


@router.post("/admin/import/preview", response_model=AlumniImportPreviewResponse)
async def preview_alumni_import(
    file: UploadFile = File(...), user: User = Depends(admin_only), db: AsyncSession = Depends(get_db),
):
    content = await file.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        from app.core.exceptions import ResourceConflictException
        raise ResourceConflictException("CSV file must be 5 MB or smaller.")
    return await AlumniService(db).preview_import(content)


@router.post("/admin/import", response_model=AlumniImportResponse)
async def import_alumni_csv(
    file: UploadFile = File(...), user: User = Depends(admin_only), db: AsyncSession = Depends(get_db),
):
    content = await file.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        from app.core.exceptions import ResourceConflictException
        raise ResourceConflictException("CSV file must be 5 MB or smaller.")
    return await AlumniService(db).import_csv(content)


@router.get("/{profile_id}", response_model=AlumniProfileDetailResponse)
async def alumni_profile_detail(
    profile_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    return await AlumniService(db).directory_profile(profile_id, user)
