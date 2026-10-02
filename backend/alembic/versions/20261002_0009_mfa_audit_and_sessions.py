"""forced password change, MFA, audit log, session metadata

Revision ID: 20261002_0009
Revises: 20261002_0008
Create Date: 2026-10-02

Mirrors database/migrations/010_mfa_audit_and_sessions.sql.
"""
from alembic import op

revision = "20261002_0009"
down_revision = "20261002_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT FALSE")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_secret VARCHAR(64)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_recovery_hashes TEXT[]")
    op.execute("ALTER TABLE refresh_tokens ADD COLUMN IF NOT EXISTS last_used_at TIMESTAMPTZ")
    op.execute("ALTER TABLE refresh_tokens ADD COLUMN IF NOT EXISTS ip_address VARCHAR(45)")
    op.execute("ALTER TABLE refresh_tokens ADD COLUMN IF NOT EXISTS user_agent VARCHAR(255)")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            actor_id UUID REFERENCES users(id) ON DELETE SET NULL,
            action VARCHAR(64) NOT NULL,
            entity_type VARCHAR(64) NOT NULL,
            entity_id VARCHAR(64),
            detail TEXT,
            ip_address VARCHAR(45),
            user_agent VARCHAR(255),
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_actor ON audit_logs(actor_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires_at ON refresh_tokens(expires_at)")


def downgrade() -> None:
    # The audit table is evidence: destroying it on a downgrade would erase the
    # record of who did what, so the drop is left to an explicit operator step.
    raise RuntimeError("Irreversible by design; archive audit_logs before dropping.")
