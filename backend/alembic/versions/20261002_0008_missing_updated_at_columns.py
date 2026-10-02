"""add updated_at to the 16 tables that were missing it

Revision ID: 20261002_0008
Revises: 20261002_0007
Create Date: 2026-10-02

Mirrors database/migrations/009_add_missing_updated_at.sql.

TimestampMixin maps `updated_at` on every model that mixes it in, and
SQLAlchemy selects every mapped column, so a table without the column makes
every ORM read fail with UndefinedColumn -- taking whole features (room
reservations, projects, lab inventory, notifications, resources, the AI
knowledge base) down with an HTTP 500 rather than degrading them.

Additive and idempotent: NOT NULL with a default, so Postgres backfills
existing rows without a table rewrite.
"""
from alembic import op

revision = "20261002_0008"
down_revision = "20261002_0007"
branch_labels = None
depends_on = None

TABLES = [
    "academic_resources",
    "ai_chat_sessions",
    "ai_chat_messages",
    "ai_generated_study_plans",
    "knowledge_documents",
    "document_chunks",
    "equipment_assets",
    "damage_reports",
    "equipment_borrow_requests",
    "projects",
    "project_publications",
    "supervisor_proposals",
    "room_reservations",
    "student_portfolios",
    "user_devices",
    "attendance_sessions",
]


def upgrade() -> None:
    for table in TABLES:
        op.execute(
            f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS "
            "updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP"
        )


def downgrade() -> None:
    # Dropping the column would put the database back into a state where those
    # endpoints 500, so this refuses rather than pretending to be reversible.
    raise RuntimeError("Irreversible: dropping updated_at reintroduces UndefinedColumn errors.")
