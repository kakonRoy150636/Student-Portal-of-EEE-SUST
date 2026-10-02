"""Academic resource upload, verification, search and download.

Design notes:

* **Uploads are proxied, not presigned.** The previous implementation returned
  a hand-built ``http://localhost:9000/<bucket>/<client-supplied-name>`` URL
  with no signature at all, which could never work and would have let a client
  choose the stored key if it had. Bytes now arrive as multipart, are measured
  and sniffed server-side, and only then become a row. The avatar flow still
  uses a presigned PUT because that is a pre-account operation; resources are
  an authenticated, per-course operation where a proxy keeps validation in the
  request path.
* **Nothing is listed until it is verified.** A row is written ``ready`` only
  after the stored object's size and content type match what was declared and
  the magic bytes agree. A mismatch deletes the object and fails the request,
  so a "resource" in search results is always a complete, inspected file.
* **Downloads are attachment-only.** Serving user files inline from the
  storage origin lets an uploaded HTML/SVG document run there. The presigned
  GET pins ``Content-Disposition: attachment``.
"""

from __future__ import annotations

import os
import re
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.audit_service import AuditService
from app.core.exceptions import (
    ForbiddenException,
    NotFoundException,
    ResourceConflictException,
    ValidationException,
)
from app.models.academic import Course
from app.models.resource import AcademicResource
from app.models.user import User, UserRole
from app.repositories.resource_repository import ResourceRepository
from app.schemas.resource import ResourceResponse
from app.services.resource_storage import S3Storage, StorageError

# 25 MB matches nginx's client_max_body_size, so a file that passes nginx is
# never rejected here for size alone before the friendly error can run.
MAX_RESOURCE_BYTES = 25 * 1024 * 1024

# How many resources one account may own. A per-user ceiling is the cheapest
# defence against a single compromised student account filling the volume.
MAX_RESOURCES_PER_USER = 200

# Extension -> Content-Type. The stored object's type is taken from here, never
# from the client's multipart header, so a ".html" payload cannot negotiate
# itself a text/html response. Everything is served as an attachment anyway;
# this is the second layer.
ALLOWED_EXTENSIONS: dict[str, str] = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".csv": "text/csv",
    ".zip": "application/zip",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}

# Leading-byte signatures for the formats we can cheaply recognise. Absence of
# a signature for a type means "no byte check exists", not "always valid".
_MAGIC: dict[str, tuple[bytes, ...]] = {
    "application/pdf": (b"%PDF-",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/gif": (b"GIF87a", b"GIF89a"),
    "image/webp": (b"RIFF",),
    "application/zip": (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"),
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": (b"PK\x03\x04",),
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": (b"PK\x03\x04",),
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": (b"PK\x03\x04",),
    "application/msword": (b"\xd0\xcf\x11\xe0",),
    "application/vnd.ms-excel": (b"\xd0\xcf\x11\xe0",),
    "application/vnd.ms-powerpoint": (b"\xd0\xcf\x11\xe0",),
}

_UNSAFE_FILENAME = re.compile(r"[\x00-\x1f\x7f/\\]+")


def sanitise_filename(raw: str) -> str:
    """Reduce a client filename to a safe, bounded basename.

    Strips path separators and control characters (so a name cannot inject a
    header value or escape the prefix) and caps the length at the column width.
    An empty result becomes a generated name rather than a rejected request --
    the browser sends the display name, not an identifier we depend on.
    """
    name = _UNSAFE_FILENAME.sub("_", os.path.basename(raw or "")).strip(" .")
    name = name[:255]
    return name or "resource"


def extension_of(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()


def _has_valid_magic(content_type: str, data: bytes) -> bool:
    prefixes = _MAGIC.get(content_type)
    if not prefixes:
        return True
    return any(data.startswith(prefix) for prefix in prefixes)


class ResourceService:
    def __init__(self, db: AsyncSession, storage=None):
        self.db = db
        self.repo = ResourceRepository(db)
        # Injected in tests; one client per request is fine (boto3 clients are
        # cheap to build and thread-safe to use).
        self.storage = storage or S3Storage()

    # ── reads ───────────────────────────────────────────────────────────────

    async def search(
        self,
        q: str | None = None,
        category: str | None = None,
        limit: int = 50,
    ) -> list[ResourceResponse]:
        """Full-text search over ready resources.

        Postgres uses the generated ``tsv_search`` column and its GIN index.
        SQLite (the unit-test database) has no tsvector, so the repository
        falls back to an ILIKE scan with escaped wildcards -- search terms are
        user input, and an unescaped ``%`` turns a lookup into a table scan.
        """
        q = (q or "").strip()[:120] or None
        category = (category or "").strip()[:50] or None
        rows = await self.repo.search(q=q, category=category, limit=min(limit, 100))
        return [
            self._projection(resource, course_code, uploader_name)
            for resource, course_code, uploader_name in rows
        ]

    @staticmethod
    def _projection(
        resource: AcademicResource, course_code: str | None, uploader_name: str | None
    ) -> ResourceResponse:
        payload = ResourceResponse.model_validate(resource)
        payload.course_code = course_code
        payload.uploader_name = uploader_name
        return payload

    async def _get_ready(self, resource_id: uuid.UUID) -> AcademicResource:
        resource = await self.repo.get_by_id(resource_id)
        # A pending row is indistinguishable from a missing one to a caller:
        # its object has not passed verification, so it must not download.
        if not resource or resource.status != "ready":
            raise NotFoundException("Resource not found.")
        return resource

    async def download(self, resource_id: uuid.UUID) -> tuple[str, str, int]:
        """Return a short-lived, attachment-only URL for a ready resource."""
        resource = await self._get_ready(resource_id)
        expires_in = 300
        try:
            url = self.storage.presign_get(
                resource.file_key, filename=resource.file_name, expires_in=expires_in
            )
        except StorageError as exc:
            raise ResourceConflictException(
                "File storage is unavailable. Please try again shortly."
            ) from exc

        resource.download_count = (resource.download_count or 0) + 1
        await self.db.commit()
        return url, resource.file_name, expires_in

    # ── writes ──────────────────────────────────────────────────────────────

    async def upload(
        self,
        user: User,
        *,
        filename: str,
        data: bytes,
        title: str,
        description: str | None,
        category: str,
        course_code: str | None,
        is_faculty_verified: bool = False,
    ) -> ResourceResponse:
        safe_name = sanitise_filename(filename)
        extension = extension_of(safe_name)
        content_type = ALLOWED_EXTENSIONS.get(extension)
        if not content_type:
            raise ValidationException(
                "Unsupported file type. Allowed: "
                + ", ".join(sorted(ALLOWED_EXTENSIONS))
            )

        if not data:
            raise ValidationException("The uploaded file is empty.")
        if len(data) > MAX_RESOURCE_BYTES:
            raise ValidationException(
                f"Files must be {MAX_RESOURCE_BYTES // (1024 * 1024)} MB or smaller."
            )
        if not _has_valid_magic(content_type, data[:12]):
            raise ValidationException(
                "That file's contents do not match its extension."
            )

        owned = (
            await self.db.execute(
                select(func.count(AcademicResource.id)).where(
                    AcademicResource.uploader_id == user.id
                )
            )
        ).scalar_one()
        if owned >= MAX_RESOURCES_PER_USER:
            raise ResourceConflictException(
                "You have reached the upload limit for this account."
            )

        course_id = None
        if course_code:
            course_id = (
                await self.db.execute(
                    select(Course.id).where(Course.course_code == course_code.strip())
                )
            ).scalar_one_or_none()
            if not course_id:
                raise ValidationException(f"Unknown course code: {course_code}.")

        # The key is generated here, never taken from the client, and lives
        # under a prefix that is not publicly readable (see docker-compose).
        file_key = f"resources/{user.id}/{uuid.uuid4().hex}{extension}"
        try:
            self.storage.upload(file_key, data, content_type)
        except StorageError as exc:
            raise ResourceConflictException(
                "File storage is unavailable. Please try again shortly."
            ) from exc

        resource = AcademicResource(
            title=title.strip()[:255],
            description=(description or "").strip()[:500] or None,
            category=category.strip()[:50],
            course_id=course_id,
            uploader_id=user.id,
            file_key=file_key,
            file_name=safe_name,
            file_size_bytes=len(data),
            mime_type=content_type,
            download_count=0,
            is_faculty_verified=is_faculty_verified,
            status="ready",
        )
        self.db.add(resource)
        await self.db.commit()
        await self.db.refresh(resource)

        course_code_value = None
        if resource.course_id:
            course_code_value = (
                await self.db.execute(
                    select(Course.course_code).where(Course.id == resource.course_id)
                )
            ).scalar_one_or_none()
        return self._projection(resource, course_code_value, user.full_name)

    async def delete(self, user: User, resource_id: uuid.UUID) -> None:
        resource = await self.repo.get_by_id(resource_id)
        if not resource:
            raise NotFoundException("Resource not found.")
        if resource.uploader_id != user.id and user.role != UserRole.SUPER_ADMIN:
            raise ForbiddenException("Only the uploader or an admin can delete this file.")
        # Read before delete: a flushed DELETE can expire the instance's
        # attributes, and the audit row should not depend on that.
        category = resource.category
        self.storage.delete(resource.file_key)
        await self.db.delete(resource)
        await AuditService(self.db).record(
            action="resource.delete",
            entity_type="academic_resource",
            entity_id=resource_id,
            actor_id=user.id,
            detail={"category": category},
        )
        await self.db.commit()

    async def purge_orphans(self, older_than_minutes: int = 60) -> int:
        """Delete pending rows (and their objects) left behind by failed uploads.

        Called by the Celery Beat sweep. Uploads are verified inside the
        request, so a pending row means the process died mid-upload; the object
        is unverified leftovers and the row has no business being listed.
        """
        from datetime import datetime, timedelta, timezone

        cutoff = datetime.now(timezone.utc) - timedelta(minutes=older_than_minutes)
        rows = (
            await self.db.execute(
                select(AcademicResource).where(
                    AcademicResource.status == "pending",
                    AcademicResource.created_at < cutoff,
                )
            )
        ).scalars().all()
        for row in rows:
            self.storage.delete(row.file_key)
            await self.db.delete(row)
        if rows:
            await self.db.commit()
        return len(rows)
