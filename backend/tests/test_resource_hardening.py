import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.core.config import settings
from app.services import resource_service as module
from app.services.resource_service import ResourceService


@pytest.mark.asyncio
async def test_presigned_urls_use_public_endpoint_and_pinned_type(monkeypatch):
    client = MagicMock()
    factory = MagicMock(return_value=client)
    monkeypatch.setattr(module.boto3, "client", factory)
    payload = SimpleNamespace(file_name="notes.pdf", mime_type="application/pdf")
    result = await ResourceService(MagicMock()).create_presigned_upload(payload, SimpleNamespace(id=uuid.uuid4()))
    assert factory.call_args.kwargs["endpoint_url"] == settings.S3_PUBLIC_ENDPOINT_URL
    assert client.generate_presigned_url.call_args.kwargs["Params"]["ContentType"] == "application/pdf"
    assert result["content_type"] == "application/pdf"


@pytest.mark.asyncio
@pytest.mark.parametrize("size,content_type", [(0, "application/pdf"), (25 * 1024 * 1024 + 1, "application/pdf"), (10, "text/html")])
async def test_finalize_rejects_actual_unsafe_object(monkeypatch, size, content_type):
    client = MagicMock()
    client.head_object.return_value = {"ContentLength": size, "ContentType": content_type}
    monkeypatch.setattr(module, "_s3_client", lambda: client)
    user = SimpleNamespace(id=uuid.uuid4())
    key = f"resources/{user.id}/{uuid.uuid4().hex}.pdf"
    db = MagicMock()
    with pytest.raises(ValueError):
        await ResourceService(db).finalize_upload(SimpleNamespace(file_key=key), user)
    client.delete_object.assert_called_once_with(Bucket=settings.S3_BUCKET_NAME, Key=key)
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_finalize_cannot_touch_another_users_object(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(module, "_s3_client", lambda: client)
    with pytest.raises(PermissionError):
        await ResourceService(MagicMock()).finalize_upload(
            SimpleNamespace(file_key=f"resources/{uuid.uuid4()}/{uuid.uuid4().hex}.pdf"),
            SimpleNamespace(id=uuid.uuid4()),
        )
    client.head_object.assert_not_called()
