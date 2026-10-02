import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ResourceResponse(BaseModel):
    """Public shape of a resource.

    ``file_key`` is deliberately absent. The storage key used to be part of
    the row returned to every authenticated user, which handed out a direct
    object path (and, with the bucket world-readable, the bytes) for any
    resource in the department. Callers receive ``id`` and go through
    ``GET /resources/{id}/download``, which checks the row and mints a
    short-lived, attachment-disposition URL.
    """

    id: uuid.UUID
    title: str
    description: str | None = None
    category: str
    course_code: str | None = None
    file_name: str
    file_size_bytes: int
    mime_type: str
    download_count: int
    is_faculty_verified: bool
    uploader_name: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ResourceUploadResponse(BaseModel):
    resource: ResourceResponse
    message: str = "Resource uploaded."


class ResourceDownloadResponse(BaseModel):
    download_url: str
    file_name: str
    # Seconds until the signed URL stops working. The client should not cache
    # it beyond this.
    expires_in: int


class ResourceSearchParams(BaseModel):
    q: str | None = Field(default=None, max_length=120)
    category: str | None = Field(default=None, max_length=50)
    limit: int = Field(default=50, ge=1, le=100)
