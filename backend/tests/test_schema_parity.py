"""Guards against ORM/DB schema drift.

app/models/alumni.py previously declared columns (event_rsvps.slot_range,
events.capacity, scholarship_applications.document_key, ...) that neither
database/schema.sql nor the Alembic revisions ever created. These tests compare
the ORM metadata against the SQL bootstrap file so the same drift cannot be
reintroduced silently.
"""
import re
from pathlib import Path

import pytest

from app.models.base import Base
import app.models  # noqa: F401  (registers every mapper)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_SQL = REPO_ROOT / "database" / "schema.sql"
MIGRATIONS_DIR = REPO_ROOT / "database" / "migrations"


def _table_names_in_schema_sql() -> set[str]:
    text = SCHEMA_SQL.read_text(encoding="utf-8")
    return set(re.findall(r"CREATE TABLE (?:IF NOT EXISTS )?(\w+)", text, flags=re.IGNORECASE))


def _columns_for_table(table: str) -> set[str]:
    text = SCHEMA_SQL.read_text(encoding="utf-8")
    match = re.search(
        rf"CREATE TABLE (?:IF NOT EXISTS )?{table}\s*\((.*?)\n\);",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    assert match, f"CREATE TABLE {table} not found in schema.sql"
    body = match.group(1)
    columns: set[str] = set()
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("--", "CONSTRAINT", "PRIMARY KEY", "UNIQUE", "CHECK", "EXCLUDE")):
            continue
        token = stripped.split()[0]
        columns.add(token.lower())
    return columns


@pytest.mark.parametrize(
    "table",
    ["events", "event_rsvps", "scholarship_applications", "alumni_profiles", "mentorship_pairs"],
)
def test_orm_table_exists_in_schema_sql(table):
    assert table in _table_names_in_schema_sql(), f"{table} missing from schema.sql"


@pytest.mark.parametrize(
    ("table", "column"),
    [
        ("events", "event_type"),
        ("events", "capacity"),
        ("events", "announced_at"),
        ("event_rsvps", "slot_range"),
        ("scholarship_applications", "document_key"),
        ("scholarship_applications", "document_name"),
        ("alumni_profiles", "is_visible"),
        ("profiles_faculty", "research_areas"),
    ],
)
def test_orm_column_exists_in_schema_sql(table, column):
    assert column in _columns_for_table(table), f"{table}.{column} missing from schema.sql"


@pytest.mark.parametrize(
    ("table", "column"),
    [
        ("events", "slot_range"),
        ("event_rsvps", "capacity"),
    ],
)
def test_absent_column_stays_absent(table, column):
    assert column not in _columns_for_table(table)


def test_every_orm_table_is_created_in_schema_sql():
    """The reverse direction: any table added to the ORM must be bootstrapped."""
    missing = sorted(
        table for table in Base.metadata.tables if table not in _table_names_in_schema_sql()
    )
    assert not missing, f"ORM tables absent from schema.sql: {missing}"


def test_parity_migration_exists_and_is_idempotent():
    migration = MIGRATIONS_DIR / "004_alumni_model_parity.sql"
    assert migration.exists(), "004_alumni_model_parity.sql is missing"
    text = migration.read_text(encoding="utf-8")
    # Every additive statement must be guarded so re-running is a no-op.
    for column in ("slot_range", "event_type", "capacity", "announced_at",
                   "document_key", "document_name", "is_visible"):
        assert f"ADD COLUMN IF NOT EXISTS {column}" in text, f"{column} is not idempotent"
