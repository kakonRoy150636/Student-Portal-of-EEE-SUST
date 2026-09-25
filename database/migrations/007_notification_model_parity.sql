-- Align `notifications` with app/models/notification.py.
--
-- The ORM declares three columns that neither schema.sql nor any earlier
-- migration ever created:
--
--   * class_session_id  -- the class_schedules row the alert is about, which is
--                          what makes the Celery Beat 1-minute scanner
--                          idempotent (one alert per recipient per session).
--   * notified_at       -- set when the broadcast actually goes out.
--   * updated_at        -- required by TimestampMixin.
--
-- Because SQLAlchemy selects every mapped column, ANY read of notifications
-- raised `column notifications.class_session_id does not exist` -- a 500 on
-- GET /notifications and on every scanner tick. Existing rows are unaffected:
-- all three columns are nullable or defaulted.
--
-- Idempotent: every statement is guarded, so re-running is a no-op.
--
-- Mirrors backend/alembic/versions/20260918_0006_notification_model_parity.py

-- Columns first: the unique constraint below keys on class_session_id, so it
-- cannot be added until the column exists.
ALTER TABLE notifications
    ADD COLUMN IF NOT EXISTS class_session_id UUID REFERENCES class_schedules(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS notified_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;

-- Deferrable so a notification referencing a session can be inserted in the
-- same transaction that creates it. NULL class_session_id rows (ordinary
-- notifications) never collide under Postgres unique semantics.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_notification_class_session'
    ) THEN
        ALTER TABLE notifications
            ADD CONSTRAINT uq_notification_class_session
            UNIQUE (recipient_id, class_session_id) DEFERRABLE INITIALLY DEFERRED;
    END IF;
END $$;

-- Drives the "unread notifications" badge on the post-login dashboard.
CREATE INDEX IF NOT EXISTS ix_notifications_recipient_read
    ON notifications (recipient_id, is_read);
