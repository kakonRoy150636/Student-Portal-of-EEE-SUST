"""Academic resource endpoints.

Thin by design: validate with Pydantic, delegate to ResourceService, return a
response model. Every read/write route requires an authenticated session, and
the object store is never addressed directly from the client.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.resource import (
    DownloadUrlResponse,
    FinalizeResourceRequest,
    FinalizeResourceResponse,
    PresignedUploadRequest,
    PresignedUploadResponse,
    ResourceResponse,
)
from app.services.resource_service import ResourceService
from app.api.request_limits import limit_search

router = APIRouter(prefix="/resources", tags=["Resources"])


@router.get("/search", response_model=list[ResourceResponse], dependencies=[Depends(limit_search)])
async def search(
    q: str | None = Query(default=None, max_length=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await ResourceService(db).search_resources(q)


@router.post("/presigned-upload", response_model=PresignedUploadResponse)
async def presigned_upload(
    payload: PresignedUploadRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        return await ResourceService(db).create_presigned_upload(payload, user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


@router.post("/finalize", response_model=FinalizeResourceResponse)
async def finalize(
    payload: FinalizeResourceRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = ResourceService(db)
    try:
        resource = await service.finalize_upload(payload, user)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return FinalizeResourceResponse(
        status="finalized",
        resource_id=resource.id,
        title=resource.title,
        file_name=resource.file_name,
    )


@router.get("/{resource_id}/download", response_model=DownloadUrlResponse)
async def download(
    resource_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Mint a short-lived download URL for one resource.

    This route is what replaced the public-read bucket: the object is only
    reachable through a link the API issues after checking the caller is
    signed in.
    """
    try:
        return await ResourceService(db).issue_download_url(resource_id, user)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
