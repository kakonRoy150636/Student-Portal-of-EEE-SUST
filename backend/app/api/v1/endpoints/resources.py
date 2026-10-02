import uuid

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.core.exceptions import TooManyRequestsException, ValidationException
from app.core.rate_limit import check_rate_limit
from app.models.user import User, UserRole
from app.schemas.resource import (
    ResourceDownloadResponse,
    ResourceResponse,
    ResourceUploadResponse,
)
from app.services.resource_service import MAX_RESOURCE_BYTES, ResourceService

router = APIRouter(prefix="/resources", tags=["Resources"])

# Faculty and admins may mark a file as faculty-verified; students cannot.
VERIFIER_ROLES = [UserRole.TEACHER, UserRole.SUPER_ADMIN]


@router.get("/search", response_model=list[ResourceResponse])
async def search(
    q: str | None = Query(default=None, max_length=120),
    category: str | None = Query(default=None, max_length=50),
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Verified resources only, newest first. Matches title and description."""
    return await ResourceService(db).search(q=q, category=category, limit=limit)


@router.post("", response_model=ResourceUploadResponse, status_code=201)
async def upload_resource(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(..., min_length=2, max_length=255),
    category: str = Form(..., min_length=2, max_length=50),
    description: str | None = Form(default=None, max_length=500),
    course_code: str | None = Form(default=None, max_length=12),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload a course resource (multipart).

    The body is read in full before validation so the magic-byte check sees
    the real header; ``MAX_RESOURCE_BYTES`` bounds how much can be buffered,
    and nginx caps the request body at the same figure upstream.
    """
    if not await check_rate_limit(f"resource-upload:{user.id}", limit=20, window_seconds=3600):
        raise TooManyRequestsException("Too many uploads. Please try again later.")

    data = await file.read(MAX_RESOURCE_BYTES + 1)
    if len(data) > MAX_RESOURCE_BYTES:
        raise ValidationException(
            f"Files must be {MAX_RESOURCE_BYTES // (1024 * 1024)} MB or smaller."
        )

    resource = await ResourceService(db).upload(
        user,
        filename=file.filename or "resource",
        data=data,
        title=title,
        description=description,
        category=category,
        course_code=course_code,
        is_faculty_verified=user.role in VERIFIER_ROLES,
    )
    return ResourceUploadResponse(resource=resource, message="Resource uploaded.")


@router.get("/{resource_id}/download", response_model=ResourceDownloadResponse)
async def download_resource(
    resource_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Mint a short-lived download URL for a verified resource.

    Returns a URL rather than the bytes so the API worker is not tied up
    streaming a 25 MB file; the signature carries the authorisation and the
    response is forced to ``attachment``.
    """
    url, filename, expires_in = await ResourceService(db).download(resource_id)
    return ResourceDownloadResponse(
        download_url=url, file_name=filename, expires_in=expires_in
    )


@router.delete("/{resource_id}", status_code=204)
async def delete_resource(
    resource_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a resource: the uploader or an admin, nobody else."""
    await ResourceService(db).delete(user, resource_id)
