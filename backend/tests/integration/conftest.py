"""Real migrated PostgreSQL per test; no create_all/type/constraint substitutes.

A session-scoped migrated template is cloned into a random database for each
test. Independent connections can really commit/block/deadlock. Redis is also
real and disposable. Parent SQLite/fake-budget fixtures are not used here.
"""
import asyncio
import os
from pathlib import Path
import subprocess
import sys
import uuid

import asyncpg
import pytest
import pytest_asyncio
import redis.asyncio as redis
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core import rate_limit, request_limits
from app.core.database import get_db
from app.main import app
from tests.integration.factories import Factory

ADMIN_URL = os.environ.get("INTEGRATION_DATABASE_URL")
REDIS_URL = os.environ.get("INTEGRATION_REDIS_URL")
BACKEND = Path(__file__).resolve().parents[2]


def pytest_collection_modifyitems(items):
    if not ADMIN_URL or not REDIS_URL:
        for item in items:
            if '/integration/' in str(item.path):
                item.add_marker(pytest.mark.skip(reason="Run docker-compose.test.yml for real PostgreSQL/Redis"))


@pytest.fixture(scope="session")
def migrated_template():
    url = make_url(ADMIN_URL).set(drivername="postgresql")
    name = 'portal_template_' + uuid.uuid4().hex
    async def manage(sql):
        conn = await asyncpg.connect(url.render_as_string(hide_password=False))
        try:
            await conn.execute(sql)
        finally:
            await conn.close()
    asyncio.run(manage(f'CREATE DATABASE "{name}"'))
    try:
        migration_url = url.set(drivername='postgresql+asyncpg', database=name)
        result = subprocess.run(
            [sys.executable, '-m', 'alembic', 'upgrade', 'head'], cwd=BACKEND,
            env={**os.environ, 'DATABASE_URL': migration_url.render_as_string(hide_password=False)},
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        yield name
    finally:
        asyncio.run(manage(f'DROP DATABASE "{name}" WITH (FORCE)'))


@pytest_asyncio.fixture
async def database(migrated_template):
    url = make_url(ADMIN_URL).set(drivername='postgresql')
    admin = await asyncpg.connect(url.render_as_string(hide_password=False))
    name = 'portal_case_' + uuid.uuid4().hex
    await admin.execute(f'CREATE DATABASE "{name}" TEMPLATE "{migrated_template}"')
    dsn = url.set(database=name).render_as_string(hide_password=False)
    engine = create_async_engine(url.set(database=name, drivername='postgresql+asyncpg'), pool_size=8)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    conn = await asyncpg.connect(dsn)
    try:
        yield Factory(conn, dsn, factory)
    finally:
        app.dependency_overrides.clear()
        await conn.close()
        await engine.dispose()
        await admin.execute(f'DROP DATABASE "{name}" WITH (FORCE)')
        await admin.close()


@pytest.fixture(autouse=True)
def reset_throttle_redis_client():
    yield  # real_redis owns the connection lifetime in this suite


@pytest.fixture(autouse=True)
def isolated_request_budgets():
    # Override the parent's fake fixture. The fixture below supplies real Redis.
    yield


@pytest_asyncio.fixture(autouse=True)
async def real_redis(monkeypatch):
    store = redis.from_url(REDIS_URL, decode_responses=True)
    await store.ping()  # infrastructure failure fails the run, never silently skips
    await store.flushdb()  # test stack's dedicated DB 15 only
    monkeypatch.setattr(rate_limit, '_redis', store)
    monkeypatch.setattr(request_limits, '_get_redis', lambda: store)
    try:
        yield store
    finally:
        await store.flushdb()
        await store.aclose()


@pytest_asyncio.fixture
async def api(database):
    async def sessions():
        async with database.sessions() as db:
            try:
                yield db
                await db.commit()
            except Exception:
                await db.rollback()
                raise
    app.dependency_overrides[get_db] = sessions
    # ASGITransport still exercises the actual routes/dependencies/transactions.
    # Lifespan is intentionally excluded: no bootstrap administrator is created.
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        yield client
