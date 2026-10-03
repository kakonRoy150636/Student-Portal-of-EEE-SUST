"""Durable notification events, batches, device deliveries and preferences.

Revision ID: 20261003_0007
Revises: 20260918_0006
Create Date: 2026-10-03
"""

from alembic import op

revision = "20261003_0007"
down_revision = "20260918_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE notification_preferences
            ADD COLUMN per_type JSONB NOT NULL DEFAULT '{}'::jsonb,
            ADD COLUMN quiet_start TIME,
            ADD COLUMN quiet_end TIME
        """
    )
    op.execute(
        """
        CREATE TABLE device_tokens (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token TEXT NOT NULL UNIQUE,
            platform VARCHAR(20) NOT NULL DEFAULT 'web',
            last_seen TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute("CREATE INDEX ix_device_tokens_user_id ON device_tokens (user_id)")
    op.execute(
        """
        INSERT INTO device_tokens (id, user_id, token, platform, last_seen, created_at)
        SELECT id, user_id, fcm_token, platform, created_at, created_at
        FROM user_devices
        WHERE is_active = TRUE
        ON CONFLICT (token) DO NOTHING
        """
    )
    op.execute(
        """
        CREATE TABLE notification_batches (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            type VARCHAR(40) NOT NULL,
            priority VARCHAR(10) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            due_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute(
        """
        CREATE TABLE notification_log (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            event_id UUID NOT NULL,
            type VARCHAR(40) NOT NULL,
            priority VARCHAR(10) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            notification_id BIGINT REFERENCES notifications(id) ON DELETE SET NULL,
            batch_id UUID REFERENCES notification_batches(id) ON DELETE SET NULL,
            due_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_notification_log_event UNIQUE (user_id, event_id, type),
            CONSTRAINT ck_notification_log_priority CHECK (priority IN ('high', 'medium', 'low'))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE notification_deliveries (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            batch_id UUID NOT NULL REFERENCES notification_batches(id) ON DELETE CASCADE,
            device_id UUID REFERENCES device_tokens(id) ON DELETE SET NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            attempts INT NOT NULL DEFAULT 0,
            attempted_at TIMESTAMPTZ,
            next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_error VARCHAR(40),
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_notification_delivery_device UNIQUE (batch_id, device_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_notification_log_pending ON notification_log (user_id, type, due_at) "
        "WHERE status = 'pending'"
    )
    op.execute(
        "CREATE INDEX ix_notification_batches_pending_due ON notification_batches (due_at) "
        "WHERE status = 'pending'"
    )
    op.execute(
        "CREATE INDEX ix_notification_deliveries_retry "
        "ON notification_deliveries (batch_id, status, next_attempt_at)"
    )
    op.execute(
        "CREATE INDEX ix_class_schedules_day_start ON class_schedules (day_of_week, start_time)"
    )
    op.execute(
        "CREATE INDEX ix_course_enrollments_notification_recipients "
        "ON course_enrollments (course_offering_id, student_id) "
        "WHERE status IN ('enrolled', 'main', 'improvement')"
    )
    op.execute("CREATE INDEX ix_semesters_active ON semesters (id) WHERE is_active = TRUE")


def downgrade() -> None:
    op.execute("DROP INDEX ix_semesters_active")
    op.execute("DROP INDEX ix_course_enrollments_notification_recipients")
    op.execute("DROP INDEX ix_class_schedules_day_start")
    # Dropping these tables removes only their own indexes and constraints.
    op.execute("DROP TABLE notification_deliveries")
    op.execute("DROP TABLE notification_log")
    op.execute("DROP TABLE notification_batches")
    op.execute("DROP TABLE device_tokens")
    op.execute(
        """
        ALTER TABLE notification_preferences
            DROP COLUMN quiet_end,
            DROP COLUMN quiet_start,
            DROP COLUMN per_type
        """
    )
