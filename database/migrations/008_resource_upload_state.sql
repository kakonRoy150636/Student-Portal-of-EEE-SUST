-- Resource upload lifecycle + storage/model parity.
--
-- Three problems this migration closes:
--
-- 1. academic_resources had no way to represent a half-finished upload. The
--    old flow presigned an arbitrary client-supplied key and never wrote a
--    row, so "list resources" could not tell a real resource from an orphaned
--    object, and nothing could clean one up. `status` ('pending' | 'ready')
--    now marks a row created at presign/multipart time and flipped once the
--    stored object has been measured and verified server-side.
--
-- 2. course_id was NOT NULL, which forced every upload to claim a course it
--    might not belong to. It is now nullable: a resource may be department-
--    wide.
--
-- 3. document_chunks.embedding was declared NOT NULL in schema.sql while
--    app/models/ai_knowledge.py never mapped the column at all. A chunk
--    written through the ORM (the AI ingestion task) would therefore fail on
--    the NOT NULL, and any SELECT * read of the table would come back with a
--    column the mapper did not know. Nullable is the honest state while an
--    installation has no embedding model configured.
--
-- Idempotent: every statement is guarded, so re-running is a no-op.
--
-- Mirrors backend/alembic/versions/20261002_0007_resource_upload_state.py

ALTER TABLE academic_resources
    ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'ready';

ALTER TABLE academic_resources ALTER COLUMN course_id DROP NOT NULL;

ALTER TABLE academic_resources
    DROP CONSTRAINT IF EXISTS academic_resources_status_check;

ALTER TABLE academic_resources
    ADD CONSTRAINT academic_resources_status_check
    CHECK (status IN ('pending', 'ready'));

CREATE INDEX IF NOT EXISTS ix_academic_resources_status
    ON academic_resources (status);

ALTER TABLE document_chunks ALTER COLUMN embedding DROP NOT NULL;
