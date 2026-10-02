"""Resource schemas.

Deliberately explicit response models: the search endpoint previously returned
ORM objects directly, which shipped every column -- including ``file_key`` --
to any authenticated caller. ``file_key`` is the object-store path, so leaking
it hands out a direct reference to the blob; it is not needed by the client,
which downloads through the API instead. See M-3 in the review.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ResourceResponse(BaseModel):
    """Public view of an academic resource. Note the absence of file_key."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None = None
    category: str
    course_id: uuid.UUID
    file_name: str
    file_size_bytes: int
    mime_type: str
    download_count: int
    is_faculty_verified: bool
    created_at: datetime


class PresignedUploadRequest(BaseModel):
    file_name: str = Field(min_length=1, max_length=255)
    file_size: int = Field(gt=0, le=25 * 1024 * 1024)
    mime_type: str = Field(min_length=1, max_length=100)


class PresignedUploadResponse(BaseModel):
    upload_url: str
    file_key: str
    expires_in: int
    # The client must send exactly this, or the signature will not match. It is
    # echoed back so the browser does not have to guess how the API encoded it.
    content_type: str


class FinalizeResourceRequest(BaseModel):
    file_key: str = Field(min_length=1, max_length=512)
    title: str = Field(min_length=1, max_length=255)
    category: str = Field(min_length=1, max_length=50)
    course_code: str = Field(min_length=1, max_length=12)
    file_name: str = Field(min_length=1, max_length=255)
    file_size_bytes: int = Field(gt=0, le=25 * 1024 * 1024)
    mime_type: str = Field(min_length=1, max_length=100)


class FinalizeResourceResponse(BaseModel):
    status: str
    resource_id: uuid.UUID
    title: str
    file_name: str


class DownloadUrlResponse(BaseModel):
    download_url: str
    expires_in: int
    file_name: str
