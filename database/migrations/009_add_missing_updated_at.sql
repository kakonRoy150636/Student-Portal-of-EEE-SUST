-- Add updated_at to every table whose ORM model maps it.
--
-- app/models/base.py's TimestampMixin declares created_at *and* updated_at,
-- and every model that mixes it in gets both mapped columns. Sixteen tables
-- were created without updated_at -- neither schema.sql nor migration 006 ever
-- emitted it -- so SQLAlchemy, which selects every mapped column, raised
-- `column <table>.updated_at does not exist` on PostgreSQL. That is a 500 on:
--
--   * GET/POST /rooms/reservations        (room_reservations)
--   * GET /projects, dashboard project tiles (projects, supervisor_proposals)
--   * GET /labs/equipment                 (equipment_assets)
--   * GET /notifications                  (user_devices, notifications fixed in 007)
--   * GET /resources/search               (academic_resources)
--   * POST /ai/query                      (knowledge_documents, document_chunks, ai_*)
--   * GET /attendance/...                 (attendance_sessions)
--   * GET /career/opportunities           (student_portfolios)
--
-- Note the failure mode: the *whole row* is unreadable, not just the missing
-- column, so this silently disabled features rather than degrading them.
--
-- Purely additive and idempotent: the column is nullable-free but defaulted,
-- so existing rows are backfilled by PostgreSQL without a table rewrite.
ALTER TABLE academic_resources        ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE ai_chat_sessions          ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE ai_chat_messages          ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE ai_generated_study_plans  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE knowledge_documents       ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE document_chunks           ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE equipment_assets          ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE damage_reports            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE equipment_borrow_requests ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE projects                  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE project_publications      ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE supervisor_proposals      ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE room_reservations         ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE student_portfolios        ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE user_devices              ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE attendance_sessions       ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
