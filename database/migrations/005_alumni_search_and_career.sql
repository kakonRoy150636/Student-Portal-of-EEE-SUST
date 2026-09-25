-- Alumni directory full-text search + career portal bridge columns.
-- Idempotent: safe to re-run on a database already patched by 003/004.

-- 1. Generated tsvector for alumni directory search (batch, department,
--    company, industry, designation). Mirrors academic_resources.tsv_search.
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
    ) STORED;

CREATE INDEX IF NOT EXISTS ix_alumni_profiles_search
    ON alumni_profiles USING GIN (search_tsv);

-- 2. career_opportunities.updated_at is required by TimestampMixin; the
--    original CREATE TABLE only had created_at, so ORM inserts would fail.
ALTER TABLE career_opportunities
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
