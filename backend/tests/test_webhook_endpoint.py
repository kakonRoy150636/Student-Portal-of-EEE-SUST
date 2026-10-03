import hashlib
import hmac

import pytest

from app.core.config import settings
from app.integrations.github_client import verify_github_signature

pytestmark = pytest.mark.asyncio


async def test_webhook_requires_signature_over_exact_bytes(client, monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_WEBHOOK_SECRET", "test-webhook-secret")
    body = b'{"zen":"test"}'
    signature = "sha256=" + hmac.new(b"test-webhook-secret", body, hashlib.sha256).hexdigest()
    headers = {"X-Hub-Signature-256": signature, "X-GitHub-Event": "ping"}
    assert (await client.post("/api/v1/webhooks/github", content=body)).status_code == 401
    assert (await client.post("/api/v1/webhooks/github", content=body+b" ", headers=headers)).status_code == 401
    result = await client.post("/api/v1/webhooks/github", content=body, headers=headers)
    assert result.status_code == 200
    assert result.json()["status"] == "verified"
    assert not verify_github_signature(body, "test-webhook-secret", "sha256=" + "é" * 64)


async def test_webhook_disabled_without_secret_and_bounded(client, monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_WEBHOOK_SECRET", "")
    assert (await client.post("/api/v1/webhooks/github", content=b"{}")).status_code == 503
    monkeypatch.setattr(settings, "GITHUB_WEBHOOK_SECRET", "test")
    assert (await client.post("/api/v1/webhooks/github", content=b"x" * (1024*1024+1))).status_code == 413
