import asyncio
import os
import uuid
from unittest.mock import AsyncMock

import pytest
import redis.asyncio as redis
from redis.exceptions import ConnectionError
from fastapi import HTTPException

from app.core import request_limits as module
from app.core.config import settings
from tests.conftest import auth_header

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize("method,path,body,scope", [
    ("POST", "/auth/login", {"identifier": "test", "password": "test"}, "login"),
    ("POST", "/auth/refresh", None, "refresh"),
    ("POST", "/ai/query", {"prompt": "Test question", "course_code": "EEE 311"}, "ai"),
    ("GET", "/resources/search", None, "resource-search"),
])
async def test_routes_enforce_budget(client, student, monkeypatch, method, path, body, scope):
    fake = AsyncMock()
    fake.eval.return_value = [1000, 42]
    monkeypatch.setattr(module, "_get_redis", lambda: fake)
    result = await client.request(method, "/api/v1" + path, json=body, headers=auth_header(student))
    assert result.status_code == 429, result.text
    assert result.headers["Retry-After"] == "42"
    assert f":{scope}:" in fake.eval.call_args.args[2]


async def test_production_rate_limit_fails_closed(monkeypatch):
    fake = AsyncMock()
    fake.eval.side_effect = ConnectionError("unavailable")
    monkeypatch.setattr(module, "_get_redis", lambda: fake)
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    with pytest.raises(HTTPException) as error:
        await module.enforce_request_limit("login", "ip", 30)
    assert error.value.status_code == 503


@pytest.mark.skipif(not os.environ.get("SECURITY_TEST_REDIS_URL"), reason="Requires test Redis")
async def test_real_redis_atomic_budget_and_expiry(monkeypatch):
    store = redis.from_url(os.environ["SECURITY_TEST_REDIS_URL"], decode_responses=True)
    monkeypatch.setattr(module, "_get_redis", lambda: store)
    scope = "test-" + uuid.uuid4().hex
    async def attempt():
        try:
            await module.enforce_request_limit(scope, "same-user", 5, 1)
            return 200
        except HTTPException as exc:
            return exc.status_code
    try:
        results = await asyncio.gather(*(attempt() for _ in range(20)))
        assert results.count(200) == 5
        assert results.count(429) == 15
        await asyncio.sleep(1.1)
        assert await attempt() == 200
    finally:
        async for key in store.scan_iter(f"portal:limit:{scope}:*"):
            await store.delete(key)
        await store.aclose()
