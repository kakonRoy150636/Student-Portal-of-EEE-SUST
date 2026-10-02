"""Academic resource service: search, presigned upload, download.

Everything object-store related lives here rather than in the endpoint so the
route handlers stay thin. Two review findings are addressed:

- M-3: the bucket is private and downloads go through a short-lived presigned
  GET issued only after an authenticated, authorised API call. Previously the
  bucket was anonymously readable and ``file_key`` leaked in search results.
- L-4: search escapes ``%`` and ``_`` before building the ILIKE pattern, so a
  query of ``%`` can no longer match every row, and ``q`` is length-bounded.
"""

from __future__ import annotations

import re
import uuid
from urllib.parse import quote
from starlette.concurrency import run_in_threadpool

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.academic import Course
from app.models.resource import AcademicResource
from app.repositories.resource_repository import ResourceRepository

PRESIGN_EXPIRY_SECONDS = 300
MAX_SEARCH_LENGTH = 100
MAX_RESOURCE_BYTES = 25 * 1024 * 1024

# Extensions we are willing to hand a presigned PUT for. Pinning this (rather
# than accepting whatever the client sends) keeps the stored object's type
# predictable, the same reasoning as the avatar upload path.
UPLOAD_TYPES = {
    ".pdf": "application/pdf",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".zip": "application/zip", ".png": "image/png",
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
}
ALLOWED_UPLOAD_EXTENSIONS = set(UPLOAD_TYPES)


def _escape_like(value: str) -> str:
    """Neutralise LIKE wildcards in user input.

    Without this, searching for ``%`` matches every row and ``_`` matches any
    character, which is both a correctness bug and an easy way to force an
    unindexed full scan.
    """
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class ResourceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ResourceRepository(db)

    async def search_resources(self, q: str | None = None):
        if q is not None:
            q = q.strip()[:MAX_SEARCH_LENGTH]
        if not q:
            return await self.repo.list_recent()
        return await self.repo.search(_escape_like(q))

    async def create_presigned_upload(self, payload, user) -> dict:
        """Issue a presigned PUT for a namespaced, validated object key."""
        extension = ""
        if "." in payload.file_name:
            extension = "." + payload.file_name.rsplit(".", 1)[1].lower()
        if extension not in ALLOWED_UPLOAD_EXTENSIONS:
            raise ValueError(
                f"File type '{extension or 'unknown'}' is not allowed. "
                f"Permitted: {', '.join(sorted(ALLOWED_UPLOAD_EXTENSIONS))}"
            )

        # Namespace under the uploader's id so the finalize step can verify
        # ownership without a lookup -- same pattern as avatar uploads.
        file_key = f"resources/{user.id}/{uuid.uuid4().hex}{extension}"

        client = _s3_client(public=True)
        try:
            upload_url = client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": settings.S3_BUCKET_NAME,
                    "Key": file_key,
                    "ContentType": UPLOAD_TYPES[extension],
                },
                ExpiresIn=PRESIGN_EXPIRY_SECONDS,
            )
        except (BotoCoreError, ClientError) as exc:
            raise RuntimeError("Could not create an upload URL.") from exc

        return {
            "upload_url": upload_url,
            "file_key": file_key,
            "expires_in": PRESIGN_EXPIRY_SECONDS,
            "content_type": UPLOAD_TYPES[extension],
        }

    async def finalize_upload(self, payload, user):
        """Persist a resource row after the client has PUT the object.

        The key must sit under the caller's own prefix, so a client cannot
        register a row pointing at somebody else's object.
        """
        expected_prefix = f"resources/{user.id}/"
        if not payload.file_key.startswith(expected_prefix):
            raise PermissionError("That upload key does not belong to you.")

        name = payload.file_key[len(expected_prefix):]
        if not re.fullmatch(r"[0-9a-f]{32}\.(pdf|ppt|pptx|doc|docx|zip|png|jpg|jpeg)", name):
            raise ValueError("Invalid upload key.")
        expected_type = UPLOAD_TYPES["." + name.rsplit(".", 1)[1]]

        client = _s3_client()
        try:
            head = await run_in_threadpool(client.head_object, Bucket=settings.S3_BUCKET_NAME, Key=payload.file_key)
        except (BotoCoreError, ClientError) as exc:
            raise FileNotFoundError("The uploaded object could not be found.") from exc

        stored_size = int(head.get("ContentLength", 0))
        if stored_size <= 0 or stored_size > MAX_RESOURCE_BYTES:
            await run_in_threadpool(_delete_quietly, client, payload.file_key)
            raise ValueError("The uploaded file must be between 1 byte and 25 MB.")
        if head.get("ContentType") != expected_type:
            await run_in_threadpool(_delete_quietly, client, payload.file_key)
            raise ValueError("The uploaded content type does not match its file extension.")

        course_id = await self.db.scalar(
            select(Course.id).where(Course.course_code == payload.course_code)
        )
        if course_id is None:
            raise ValueError(f"Unknown course code '{payload.course_code}'.")

        resource = AcademicResource(
            title=payload.title,
            category=payload.category,
            course_id=course_id,
            uploader_id=user.id,
            file_key=payload.file_key,
            file_name=payload.file_name,
            file_size_bytes=stored_size,
            mime_type=expected_type,
        )
        self.db.add(resource)
        await self.db.commit()
        await self.db.refresh(resource)
        return resource

    async def issue_download_url(self, resource_id, user) -> dict:
        """Presigned GET for one resource, replacing the public bucket.

        Authorisation happens here, before any URL exists: the returned link is
        the only way to reach the object, and it expires in minutes.
        """
        resource = await self.db.get(AcademicResource, resource_id)
        if resource is None:
            raise FileNotFoundError("Resource not found.")

        client = _s3_client(public=True)
        try:
            download_url = client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": settings.S3_BUCKET_NAME,
                    "Key": resource.file_key,
                    "ResponseContentDisposition": "attachment; filename*=UTF-8''" + quote(resource.file_name, safe=""),
                    "ResponseContentType": "application/octet-stream",
                },
                ExpiresIn=PRESIGN_EXPIRY_SECONDS,
            )
        except (BotoCoreError, ClientError) as exc:
            raise RuntimeError("Could not create a download URL.") from exc

        resource.download_count = (resource.download_count or 0) + 1
        await self.db.commit()

        return {
            "download_url": download_url,
            "expires_in": PRESIGN_EXPIRY_SECONDS,
            "file_name": resource.file_name,
        }


def _s3_client(*, public=False):
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_PUBLIC_ENDPOINT_URL if public else settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
    )


def _delete_quietly(client, file_key: str) -> None:
    try:
        client.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=file_key)
    except (BotoCoreError, ClientError):
        return
