"""notifications model/DB parity

Revision ID: 20260918_0006
Revises: 20260917_0005
Create Date: 2026-09-18

app/models/notification.py declares class_session_id, notified_at and
updated_at, but schema.sql created none of them, so any read of the table
raised UndefinedColumn -> GET /notifications returned 500.

Mirrors database/migrations/007_notification_model_parity.sql. All three
columns are nullable or defaulted, so existing rows are untouched.
"""
from alembic import op

revision = "20260918_0006"
down_revision = "20260917_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Columns first: the unique constraint added below keys on
    # class_session_id, so it cannot be created until the column exists.
    op.execute(
        """
        ALTER TABLE notifications
            ADD COLUMN IF NOT EXISTS class_session_id UUID
                REFERENCES class_schedules(id) ON DELETE CASCADE,
            ADD COLUMN IF NOT EXISTS notified_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ
                NOT NULL DEFAULT CURRENT_TIMESTAMP
        """
    )
    # Deferrable so a notification referencing a class session can be inserted
    # in the same transaction that creates it. NULL class_session_id rows never
    # collide under Postgres unique semantics.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'uq_notification_class_session'
            ) THEN
                ALTER TABLE notifications
                    ADD CONSTRAINT uq_notification_class_session
                    UNIQUE (recipient_id, class_session_id) DEFERRABLE INITIALLY DEFERRED;
            END IF;
        END $$
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_notifications_recipient_read
            ON notifications (recipient_id, is_read)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_notifications_recipient_read")
    op.execute(
        """
        ALTER TABLE notifications
            DROP CONSTRAINT IF EXISTS uq_notification_class_session,
            DROP COLUMN IF EXISTS class_session_id,
            DROP COLUMN IF EXISTS notified_at,
            DROP COLUMN IF EXISTS updated_at
        """
    )
