"""Object-storage adapter for academic resources.

Wraps boto3 so the service layer has one narrow, testable surface. The test
suite substitutes :class:`InMemoryStorage` (see tests), which is why every
method returns plain data instead of a boto3 response object.

Two behaviours are worth calling out:

* `presign_get` sets ``ResponseContentDisposition: attachment``. Resource
  uploads are user-supplied files, and a PDF or SVG served *inline* from the
  storage origin executes in that origin's context. Forcing a download means
  a crafted file is never rendered as a document by the browser.
* `upload` pins the ``ContentType`` from the server-side allowlist (passed in
  by the caller) rather than the client's own ``Content-Type``.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings


class StorageError(RuntimeError):
    """Raised when the object store is unreachable or refuses the call."""


@dataclass(frozen=True)
class StoredObject:
    size: int
    content_type: str


class S3Storage:
    """boto3-backed implementation used in every real deployment."""

    def __init__(self, *, public: bool = False) -> None:
        import boto3  # imported lazily so tests never need credentials

        endpoint = settings.S3_PUBLIC_ENDPOINT_URL if public else settings.S3_ENDPOINT_URL
        self._public = public
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
        )
        self._bucket = settings.S3_BUCKET_NAME

    def upload(self, key: str, data: bytes, content_type: str) -> None:
        try:
            self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=io.BytesIO(data),
                ContentType=content_type,
                ContentDisposition="attachment",
            )
        except (BotoCoreError, ClientError) as exc:  # pragma: no cover - needs S3
            raise StorageError(str(exc)) from exc

    def head(self, key: str) -> StoredObject | None:
        try:
            response = self._client.head_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if status == 404:
                return None
            raise StorageError(str(exc)) from exc
        except BotoCoreError as exc:  # pragma: no cover - needs S3
            raise StorageError(str(exc)) from exc
        return StoredObject(
            size=int(response.get("ContentLength", 0)),
            content_type=(response.get("ContentType") or "").lower(),
        )

    def read_prefix(self, key: str, length: int = 12) -> bytes:
        try:
            body = self._client.get_object(
                Bucket=self._bucket, Key=key, Range=f"bytes=0-{length - 1}"
            )["Body"]
            return body.read()
        except (BotoCoreError, ClientError):  # pragma: no cover - needs S3
            return b""

    def presign_get(self, key: str, *, filename: str, expires_in: int = 300) -> str:
        try:
            return self._client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self._bucket,
                    "Key": key,
                    "ResponseContentDisposition": f'attachment; filename="{filename}"',
                },
                ExpiresIn=expires_in,
            )
        except (BotoCoreError, ClientError) as exc:  # pragma: no cover - needs S3
            raise StorageError(str(exc)) from exc

    def delete(self, key: str) -> None:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
        except (BotoCoreError, ClientError):  # pragma: no cover - needs S3
            # Deleting is best-effort cleanup: a failure to remove an orphaned
            # object must not fail the request that is cleaning it up.
            return
