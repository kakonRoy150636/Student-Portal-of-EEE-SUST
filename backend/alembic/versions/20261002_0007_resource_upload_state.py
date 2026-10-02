"""resource upload lifecycle + document_chunks parity

Revision ID: 20261002_0007
Revises: 20260918_0006
Create Date: 2026-10-02

Mirrors database/migrations/008_resource_upload_state.sql:

* `academic_resources.status` ('pending' | 'ready') gives the upload flow a
  row to attach ownership and size to before the bytes exist.
* `academic_resources.course_id` becomes nullable -- a resource may be
  department-wide rather than tied to one course.
* `document_chunks.embedding` becomes nullable so the ORM model (which never
  mapped the column) and the schema agree; a NOT NULL column the model cannot
  write made every ingestion insert fail.
"""
from alembic import op

revision = "20261002_0007"
down_revision = "20260918_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE academic_resources
            ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'ready'
        """
    )
    op.execute("ALTER TABLE academic_resources ALTER COLUMN course_id DROP NOT NULL")
    op.execute(
        "ALTER TABLE academic_resources DROP CONSTRAINT IF EXISTS academic_resources_status_check"
    )
    op.execute(
        """
        ALTER TABLE academic_resources
            ADD CONSTRAINT academic_resources_status_check
            CHECK (status IN ('pending', 'ready'))
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_academic_resources_status
            ON academic_resources (status)
        """
    )
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding DROP NOT NULL")


def downgrade() -> None:
    # Pending rows cannot exist under the old schema (no status column, and a
    # NOT NULL course_id), so the data must be cleaned before a downgrade
    # could succeed. Refusing loudly beats a half-applied revert.
    raise RuntimeError(
        "Irreversible: resource upload state cannot be downgraded without "
        "discarding pending uploads. Roll forward instead."
    )
