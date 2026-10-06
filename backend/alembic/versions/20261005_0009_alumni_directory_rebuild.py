"""Expand the alumni directory and backfill legacy career data.

Revision ID: 20261005_0009
Revises: 20261004_0008
"""
from alembic import op

revision = "20261005_0009"
down_revision = "20261004_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing deployments already have batch_year and updated_at. These
    # guards make the migration safe for both the legacy schema and the
    # current Alembic-managed schema without rewriting existing profiles.
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM alumni_profiles WHERE batch_year < 2010) THEN
                RAISE EXCEPTION 'alumni_profiles contains batch_year values before 2010';
            END IF;
        END $$
    """)
    op.execute("""
        ALTER TABLE alumni_profiles
            ADD COLUMN IF NOT EXISTS current_city VARCHAR(120),
            ADD COLUMN IF NOT EXISTS current_country VARCHAR(120),
            ADD COLUMN IF NOT EXISTS bio VARCHAR(2000),
            ADD COLUMN IF NOT EXISTS phone VARCHAR(30),
            ADD COLUMN IF NOT EXISTS email_visible BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS phone_visible BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS is_verified BOOLEAN NOT NULL DEFAULT FALSE
    """)
    op.execute("UPDATE alumni_profiles SET is_verified = verified_by_admin WHERE is_verified IS DISTINCT FROM verified_by_admin")
    op.execute("ALTER TABLE alumni_profiles DROP CONSTRAINT IF EXISTS ck_alumni_profiles_batch_year")
    op.execute("ALTER TABLE alumni_profiles ADD CONSTRAINT ck_alumni_profiles_batch_year CHECK (batch_year >= 2010)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_alumni_profiles_current_country ON alumni_profiles (current_country)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_alumni_profiles_is_verified ON alumni_profiles (is_verified)")

    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_full_name_trgm ON users USING GIN (full_name gin_trgm_ops)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS alumni_employments (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            alumni_id UUID NOT NULL REFERENCES alumni_profiles(id) ON DELETE CASCADE,
            organization VARCHAR(255) NOT NULL,
            position VARCHAR(255) NOT NULL,
            sector VARCHAR(30) NOT NULL DEFAULT 'other',
            city VARCHAR(120),
            country VARCHAR(120),
            start_date DATE,
            end_date DATE,
            is_current BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT ck_alumni_employments_sector CHECK (
                sector IN ('industry', 'academia', 'government', 'startup', 'higher_study', 'other')
            ),
            CONSTRAINT ck_alumni_employments_dates CHECK (
                end_date IS NULL OR start_date IS NULL OR end_date >= start_date
            )
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_alumni_employments_alumni ON alumni_employments (alumni_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_alumni_employments_country_sector ON alumni_employments (country, sector)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_alumni_employments_organization_trgm ON alumni_employments USING GIN (organization gin_trgm_ops)")
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_alumni_employments_one_current
        ON alumni_employments (alumni_id) WHERE is_current
    """)

    # Preserve the existing directory data as the first current timeline row.
    # A missing legacy company is intentionally not turned into invented data.
    op.execute("""
        INSERT INTO alumni_employments (
            alumni_id, organization, position, sector, city, country, is_current
        )
        SELECT ap.id,
               ap.current_company,
               COALESCE(NULLIF(ap.designation, ''), 'Not specified'),
               CASE
                   WHEN lower(COALESCE(ap.industry, '')) IN ('academia', 'education', 'higher study') THEN 'academia'
                   WHEN lower(COALESCE(ap.industry, '')) IN ('government', 'public sector') THEN 'government'
                   WHEN lower(COALESCE(ap.industry, '')) IN ('startup', 'start-up') THEN 'startup'
                   WHEN lower(COALESCE(ap.industry, '')) IN ('higher_study', 'higher study') THEN 'higher_study'
                   ELSE 'other'
               END,
               ap.current_city,
               ap.current_country,
               TRUE
        FROM alumni_profiles ap
        WHERE NULLIF(trim(ap.current_company), '') IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM alumni_employments ae
              WHERE ae.alumni_id = ap.id AND ae.is_current
          )
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_alumni_employments_one_current")
    op.execute("DROP INDEX IF EXISTS ix_alumni_employments_organization_trgm")
    op.execute("DROP INDEX IF EXISTS ix_alumni_employments_country_sector")
    op.execute("DROP INDEX IF EXISTS ix_alumni_employments_alumni")
    op.execute("DROP TABLE IF EXISTS alumni_employments CASCADE")
    op.execute("DROP INDEX IF EXISTS ix_users_full_name_trgm")
    op.execute("ALTER TABLE alumni_profiles DROP CONSTRAINT IF EXISTS ck_alumni_profiles_batch_year")
    op.execute("ALTER TABLE alumni_profiles DROP COLUMN IF EXISTS is_verified")
    op.execute("ALTER TABLE alumni_profiles DROP COLUMN IF EXISTS phone_visible")
    op.execute("ALTER TABLE alumni_profiles DROP COLUMN IF EXISTS email_visible")
    op.execute("ALTER TABLE alumni_profiles DROP COLUMN IF EXISTS phone")
    op.execute("ALTER TABLE alumni_profiles DROP COLUMN IF EXISTS bio")
    op.execute("ALTER TABLE alumni_profiles DROP COLUMN IF EXISTS current_country")
    op.execute("ALTER TABLE alumni_profiles DROP COLUMN IF EXISTS current_city")
