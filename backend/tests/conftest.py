"""Shared pytest fixtures.

The suite runs against SQLite+aiosqlite in memory, so it needs no Postgres,
Redis, or MinIO. That means the two PostgreSQL-only features the booking flow
depends on (the GiST exclusion constraint and TSTZRANGE) are unavailable here;
tests for those are limited to service-level behaviour. The exclusion
constraint itself is asserted structurally in test_schema_parity.py.
"""
import asyncio
import os
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import JSON, MetaData, Text, UniqueConstraint, Uuid, event, text
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test_secret_key_for_unit_tests_only_not_used_in_prod")

import app.models  # noqa: F401,E402  (import for side effect: registers all mappers)
from app.core.database import get_db  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.main import app  # noqa: E402  (must come after `import app.models`:
# `import app.models` rebinds the name `app` to the package, which would
# otherwise shadow the FastAPI instance imported here)
from app.models.base import Base  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

# PostgreSQL-only column types cannot be created on SQLite, so they are patched
# out for the test run. Production keeps the real definitions.
#
# These must be real TypeEngine *instances*, not bare strings: SQLAlchemy's DDL
# compiler calls type_._variant_mapping, so assigning "CHAR(36)" raises
# AttributeError during create_all.
_PG_ONLY_TYPES = ("TSTZRANGE", "INT4RANGE", "VECTOR", "JSONB", "ARRAY", "UUID")
_PG_ONLY_FALLBACKS = {
    # Range and vector types are only ever read/written through SQL helpers
    # (lower()/upper(), int4range()), which SQLite does not implement either --
    # the parity tests assert the constraints structurally instead.
    "TSTZRANGE": Text(),
    "INT4RANGE": Text(),
    "VECTOR": Text(),
    # SQLite has native JSON, so these stay behaviourally meaningful.
    "JSONB": JSON(),
    "ARRAY": JSON(),
    # Generic Uuid renders as CHAR(32) on SQLite while still round-tripping
    # python uuid.UUID objects, which CHAR(36) would not.
    "UUID": Uuid(as_uuid=True),
}


@compiles(ExcludeConstraint, "sqlite")
def _skip_exclude_constraint(element, compiler, **kw):
    """Render PostgreSQL GiST exclusion constraints as no-ops under SQLite.

    The compiler has no visit_exclude_constraint, and the constraint's
    PostgreSQL initargs ("DEFERRABLE", "WHERE", "using gist") are not valid
    SQLite DDL, so create_all would fail on every table that declares one.
    The real constraints are asserted structurally by test_schema_parity.py.
    """
    # create_table_constraints() joins the compiled elements with ", \n\t" and
    # filters only `p is not None` -- an empty string would still join as a
    # stray comma and break every CREATE TABLE with 'near ","'. None removes
    # the element from the DDL entirely.
    return None


@compiles(UniqueConstraint, "sqlite")
def _skip_deferrable_unique(element, compiler, **kw):
    """Render a UniqueConstraint without the PostgreSQL-only DEFERRABLE tail.

    notifications.uq_notification_class_session is declared deferrable=True so
    the Celery Beat scanner can defer it, but SQLite has no DEFERRABLE syntax
    and would reject the whole CREATE TABLE. The uniqueness guarantee itself is
    unaffected -- only the timing of the check is lost in tests.
    """
    if not getattr(element, "deferrable", None):
        return None
    dialect = compiler.dialect
    preparer = dialect.identifier_preparer
    return "CONSTRAINT %s UNIQUE (%s)" % (
        preparer.quote(element.name) if element.name else "",
        ", ".join(
            preparer.quote(c.name) for c in element.columns
        ),
    )


@pytest_asyncio.fixture
async def engine():
    engine = create_async_engine(TEST_DB_URL, future=True)

    # Work on a private copy of the metadata. Substituting column types in
    # place would mutate the shared Base.metadata that the PostgreSQL fixtures
    # also build from, and whichever suite ran first would poison the other
    # (a TEXT stand-in for TSTZRANGE yields "operator does not exist: text && text").
    sqlite_metadata = MetaData()

    @compiles(ExcludeConstraint, "sqlite")
    def _noop_exclude(element, compiler, **kw):  # pragma: no cover - DDL shim
        return None

    for table in Base.metadata.sorted_tables:
        copied = table.to_metadata(sqlite_metadata)
        for column in copied.columns:
            type_str = str(column.type).upper()
            for pg_type in _PG_ONLY_TYPES:
                if type_str.startswith(pg_type):
                    column.type = _PG_ONLY_FALLBACKS[pg_type].copy()

    async with engine.begin() as conn:
        await conn.run_sync(sqlite_metadata.create_all)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db(session_factory) -> AsyncSession:
    async with session_factory() as session:
        yield session


def _make_client(factory):
    """Build an ASGI client wired to the given session factory."""

    async def _override_get_db():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest_asyncio.fixture
async def client(session_factory):
    """ASGI client with the database dependency overridden."""
    async with _make_client(session_factory) as ac:
        # No cookie jar sharing needed; the API sets its own refresh cookie.
        yield ac
    app.dependency_overrides.clear()


# The booking flow depends on two PostgreSQL features SQLite cannot provide:
# TSTZRANGE (built with tstzrange()/lower()/upper()) and the GiST EXCLUDE
# constraint that rejects overlapping slots. Rather than mock them away, those
# tests run against a real PostgreSQL when one is reachable; the shared SQLite
# engine keeps the rest of the suite dependency-free.
PG_TEST_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5433/sust_eee_test",
)


async def _postgres_reachable() -> bool:
    try:
        probe = create_async_engine(PG_TEST_URL, pool_pre_ping=True)
        async with probe.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await probe.dispose()
        return True
    except Exception:
        return False


@pytest_asyncio.fixture
async def pg_session_factory():
    """Session factory bound to a real PostgreSQL, using a throwaway schema.

    Skips when no Postgres is reachable, so `pytest` still works on a bare
    checkout. To enable these tests:
      docker compose up -d postgres
      psql -h localhost -p 5433 -U postgres -c 'CREATE DATABASE sust_eee_test'
    """
    if not await _postgres_reachable():
        pytest.skip(f"PostgreSQL not reachable at {PG_TEST_URL}")

    pg_engine = create_async_engine(PG_TEST_URL, future=True)
    schema = f"test_{uuid.uuid4().hex[:12]}"

    # Pooled connections each need the schema on their search_path, otherwise
    # they resolve tables against `public` and fail with "relation does not
    # exist". A connect event applies it to every new connection.
    @event.listens_for(pg_engine.sync_engine, "connect")
    def _set_search_path(dbapi_conn, _record):
        with dbapi_conn.cursor() as cur:
            cur.execute(f'SET search_path TO "{schema}"')

    async with pg_engine.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield async_sessionmaker(bind=pg_engine, class_=AsyncSession, expire_on_commit=False)
    finally:
        async with pg_engine.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await pg_engine.dispose()


@pytest_asyncio.fixture
async def pg_client(pg_session_factory):
    """ASGI client backed by PostgreSQL -- exercises GiST/tstzrange for real."""
    async with _make_client(pg_session_factory) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def pg_db(pg_session_factory):
    async with pg_session_factory() as session:
        yield session


async def make_user(
    db: AsyncSession,
    *,
    role: UserRole = UserRole.STUDENT,
    identifier: str | None = None,
    email: str | None = None,
    password: str = "Passw0rd!23",
    is_active: bool = True,
) -> User:
    """Persist a user with a known password and return the ORM instance."""
    suffix = uuid.uuid4().hex[:8]
    user = User(
        identifier=identifier or f"id-{suffix}",
        email=email or f"user-{suffix}@sust.edu",
        password_hash=get_password_hash(password),
        full_name=f"Test {role.value}",
        role=role,
        is_active=is_active,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def student(db) -> User:
    return await make_user(db, role=UserRole.STUDENT)


@pytest_asyncio.fixture
async def admin(db) -> User:
    return await make_user(db, role=UserRole.SUPER_ADMIN)


@pytest_asyncio.fixture
async def teacher(db) -> User:
    return await make_user(db, role=UserRole.TEACHER)


def auth_header(user: User) -> dict:
    from app.core.security import create_access_token

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}
