-- Optional semester target terms for semester-scoped course offerings.
--
-- This mirrors backend/alembic/versions/20261010_0011_semester_target_term.py
-- for deployments that apply the SQL migration directory directly.

ALTER TABLE semesters
    ADD COLUMN IF NOT EXISTS target_term VARCHAR(4);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_semesters_target_term'
          AND conrelid = 'semesters'::regclass
    ) THEN
        ALTER TABLE semesters
            ADD CONSTRAINT ck_semesters_target_term
            CHECK (
                target_term IS NULL OR target_term IN
                ('1-1', '1-2', '2-1', '2-2',
                 '3-1', '3-2', '4-1', '4-2')
            );
    END IF;
END $$;

-- Backfill only titles in the canonical "Term N-N, YYYY" form. Other
-- historical titles are intentionally left NULL and retain legacy behavior.
UPDATE semesters
SET target_term = substring(title FROM '^Term ([1-4]-[12]), [0-9]{4}$')
WHERE target_term IS NULL
  AND title ~ '^Term ([1-4]-[12]), [0-9]{4}$';
