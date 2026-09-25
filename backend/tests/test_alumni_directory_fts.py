"""Alumni directory full-text search: query and generated column must agree.

The stored ``alumni_profiles.search_tsv`` column is a generated column built
with ``to_tsvector('english', ...)`` in ``database/schema.sql`` and
``database/migrations/005_alumni_search_and_career.sql``. The repository used
to query it with ``plainto_tsquery('simple', ...)`` against a *recomputed*
``to_tsvector('simple', ...)`` expression, and its docstring cited an index
(``ix_alumni_profiles_fts``) that has never existed in this repo.

That is a correctness bug, not just a performance one: a token stemmed by one
configuration does not match the same token produced by another, so
``to_tsvector('english', 'power systems engineering') @@
plainto_tsquery('simple', 'engineering')`` is false while the
``'english'``/``'english'`` pair is true. The directory silently returned
nothing. Recomputing the expression inline also made the query structurally
different from the indexed expression, so the GIN index could not be used.

These tests pin both halves of the fix: the query the repository emits, and
the DDL the database is actually built with.
"""
import re
from pathlib import Path

import pytest
from sqlalchemy import and_, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import selectinload

from app.models.alumni import AlumniProfile
from app.repositories.alumni_repository import (
    DIRECTORY_TS_CONFIG,
    AlumniRepository,
    _directory_tsquery,
    _directory_tsvector,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
# The suite runs inside the backend image, where only /app and /database are
# mounted (the alembic revisions live at /app/alembic, not /backend/alembic),
# so each source is located by probing the layouts that exist here.
_CANDIDATES = {
    "schema.sql": [REPO_ROOT / "database" / "schema.sql", Path("/database/schema.sql")],
    "005_alumni_search_and_career.sql": [
        REPO_ROOT / "database" / "migrations" / "005_alumni_search_and_career.sql",
        Path("/database/migrations/005_alumni_search_and_career.sql"),
    ],
    "20260916_0004_alumni_search_and_career.py": [
        REPO_ROOT / "backend" / "alembic" / "versions" / "20260916_0004_alumni_search_and_career.py",
        Path("/app/alembic/versions/20260916_0004_alumni_search_and_career.py"),
    ],
    "alumni_repository.py": [
        REPO_ROOT / "backend" / "app" / "repositories" / "alumni_repository.py",
        Path("/app/app/repositories/alumni_repository.py"),
    ],
}


def _source(name: str) -> str:
    for candidate in _CANDIDATES[name]:
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")
    raise AssertionError(
        "none of the expected locations exist for %s: %s" % (name, _CANDIDATES[name])
    )


SCHEMA_SQL = _CANDIDATES["schema.sql"]


def _generated_column_config(text: str, source: str) -> str:
    """Pull the text-search configuration out of the search_tsv DDL.

    Anchors on the ``search_tsv`` declaration so it asserts on the generated
    column itself and not on some unrelated tsvector in the same file.
    """
    body = re.search(
        r"search_tsv\s+TSVECTOR\s+GENERATED ALWAYS AS\s*\((.*?)\)\s*STORED",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    assert body, f"no generated search_tsv column found in {source}"
    config = re.search(r"to_tsvector\(\s*'([a-z_]+)'", body.group(1), flags=re.IGNORECASE)
    assert config, f"search_tsv in {source} is not built with to_tsvector('config', ...)"
    return config.group(1).lower()


def _directory_search_statement(q: str):
    """Rebuild the statement search_directory() builds, without touching a DB.

    Duplicating the filter shape is deliberate: compiling a Select needs no
    live session, so this exercises the real ``_directory_tsvector()`` /
    ``_directory_tsquery()`` helpers without running the Postgres-only ``@@``
    operator against the SQLite test engine.
    """
    filters = [
        AlumniProfile.is_visible.is_(True),
        AlumniProfile.membership_status == "active",
        _directory_tsvector().op("@@")(_directory_tsquery(q)),
    ]
    return select(AlumniProfile).options(selectinload(AlumniProfile.user)).where(and_(*filters))


def _compiled_postgres_sql(q: str) -> str:
    """Compile without ``literal_binds``.

    The text-search configuration is a REGCONFIG and SQLAlchemy has no
    literal renderer for that type, so ``literal_binds`` raises a
    CompileError on the ``plainto_tsquery`` call. The bound config is
    asserted separately, from the compiled params.
    """
    return str(_directory_search_statement(q).compile(dialect=postgresql.dialect()))


def _compiled_params(q: str) -> dict:
    return _directory_search_statement(q).compile(dialect=postgresql.dialect()).params


def test_query_and_generated_column_use_the_same_config():
    """The Postgres query and schema.sql must stem with one configuration."""
    assert _generated_column_config(_source("schema.sql"), "schema.sql") == DIRECTORY_TS_CONFIG


def test_query_config_is_the_one_the_column_is_built_with():
    """The query's plainto_tsquery must bind the stored column's configuration.

    This is the assertion the original bug would have failed: the generated
    column was built with 'english' while the query bound 'simple', so
    nothing ever matched.
    """
    params = _compiled_params("engineering")
    assert params["plainto_tsquery_1"] == DIRECTORY_TS_CONFIG
    assert params["plainto_tsquery_2"] == "engineering"


@pytest.mark.parametrize(
    "name", ["005_alumni_search_and_career.sql", "20260916_0004_alumni_search_and_career.py"]
)
def test_migrations_agree_with_schema_and_repository(name: str):
    """005 and its Alembic twin must declare the same config as the query."""
    assert _generated_column_config(_source(name), name) == DIRECTORY_TS_CONFIG


def test_directory_query_targets_the_stored_search_tsv_column():
    """The query must reference search_tsv, not recompute to_tsvector.

    Referencing the column is what allows ix_alumni_profiles_search to apply:
    an expression can only use the index if it matches the indexed expression
    structurally.
    """
    sql = _compiled_postgres_sql("engineering")
    assert "alumni_profiles.search_tsv" in sql, "directory query does not use the indexed stored column"
    assert "to_tsvector" not in sql, "directory query recomputes the expression, blocking the GIN index"
    assert "@@" in sql


def test_gin_index_targets_the_same_column():
    index = re.search(
        r"CREATE INDEX (?:IF NOT EXISTS )?ix_alumni_profiles_search ON alumni_profiles USING GIN \((\w+)\)",
        _source("schema.sql"),
    )
    assert index, "ix_alumni_profiles_search missing from schema.sql"
    assert index.group(1) == "search_tsv"


def test_no_stale_fts_index_reference():
    """ix_alumni_profiles_fts does not exist and must not be cited anywhere."""
    assert "ix_alumni_profiles_fts" not in _source("alumni_repository.py")


def test_ilike_fallback_is_preserved_and_unique():
    """The SQLite fallback must still exist, exactly once (no duplicate path)."""
    assert hasattr(AlumniRepository, "search_directory_fallback")
    assert _source("alumni_repository.py").count("async def search_directory_fallback(") == 1
