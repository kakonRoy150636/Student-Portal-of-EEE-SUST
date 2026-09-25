"""alumni directory tsvector + career updated_at

Revision ID: 20260916_0004
Revises: 20260915_0003
Create Date: 2026-09-16

Adds:
  * alumni_profiles.search_tsv (generated tsvector) + GIN index
  * career_opportunities.updated_at (required by TimestampMixin)
"""
from alembic import op

revision = "20260916_0004"
down_revision = "20260915_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE alumni_profiles
            ADD COLUMN IF NOT EXISTS search_tsv tsvector
            GENERATED ALWAYS AS (
                to_tsvector(
                    'english',
                    coalesce(department, '') || ' ' ||
                    coalesce(current_company, '') || ' ' ||
                    coalesce(industry, '') || ' ' ||
                    coalesce(designation, '') || ' ' ||
                    coalesce(batch_year::text, '')
                )
            ) STORED
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_alumni_profiles_search ON alumni_profiles USING GIN (search_tsv)"
    )
    op.execute(
        """
        ALTER TABLE career_opportunities
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_alumni_profiles_search")
    op.execute("ALTER TABLE alumni_profiles DROP COLUMN IF EXISTS search_tsv")
    op.execute("ALTER TABLE career_opportunities DROP COLUMN IF EXISTS updated_at")
