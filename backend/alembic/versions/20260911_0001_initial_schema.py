"""Frozen baseline of database/schema.sql as of 2026-10-02.

Keep this revision ID: existing deployments may already have recorded it.
The formerly empty baseline now supports empty databases. Unversioned legacy
databases must be inspected and explicitly stamped before upgrading (README).
Never edit the snapshot for future changes: add a new revision instead.
"""
import re
from pathlib import Path

from alembic import op
import sqlalchemy as sa
import sqlparse

revision = '20260911_0001'
down_revision = None
branch_labels = None
depends_on = None

SNAPSHOT = Path(__file__).resolve().parents[1] / "sql" / "20260911_0001_baseline.sql"


def upgrade() -> None:
    if not op.get_context().as_sql:
        tables = set(sa.inspect(op.get_bind()).get_table_names(schema="public"))
        if tables - {"alembic_version"}:
            raise RuntimeError(
                "Unversioned, non-empty database: inspect/backup the schema and "
                "follow README's existing-database adoption steps before running upgrade. "
                "Do not stamp an arbitrary or partially initialized database."
            )
    # asyncpg prepares one statement at a time. sqlparse preserves quoted
    # strings, comments and dollar-quoted bodies, unlike split(';').
    for statement in sqlparse.split(SNAPSHOT.read_text(encoding="utf-8")):
        op.execute(sa.text(statement))

def downgrade() -> None:
    sql = SNAPSHOT.read_text(encoding="utf-8")
    # Reverse creation order respects the snapshot's FK dependencies; no
    # CASCADE, so unrelated application objects are never silently removed.
    for table in reversed(re.findall(r"^CREATE TABLE (\w+)", sql, re.MULTILINE)):
        op.execute(f'DROP TABLE IF EXISTS "{table}"')
    for name in reversed(re.findall(r"^CREATE TYPE (\w+)", sql, re.MULTILINE)):
        op.execute(f'DROP TYPE IF EXISTS "{name}"')
    # Extensions may be shared with other applications; retain them on base.
