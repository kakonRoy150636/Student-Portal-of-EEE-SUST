"""alumni model/DB parity

Revision ID: 20260915_0003
Revises: 20260914_0002
Create Date: 2026-09-15

app/models/alumni.py declared columns that neither schema.sql nor revision
0002 ever created, so any insert/select touching them failed with
UndefinedColumn:

  * events.event_type / capacity / announced_at
  * event_rsvps.slot_range (+ the no_double_booked_event_seats GiST
    exclusion constraint, which was a comment-only claim)
  * scholarship_applications.document_key / document_name
  * alumni_profiles.is_visible

This revision brings the database up to the models. It also reconciles the
scholarship application status vocabulary, which the model and the SQL
CHECK constraint disagreed on:

  legacy SQL : pending | shortlisted | awarded | rejected
  model      : submitted | under_review | approved | rejected

Existing rows are mapped forward before the CHECK is replaced. Mirrors
database/migrations/004_alumni_model_parity.sql.
"""
from alembic import op

revision = "20260915_0003"
down_revision = "20260914_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. events.
    op.execute(
        """
        ALTER TABLE events
            ADD COLUMN IF NOT EXISTS event_type VARCHAR(20) NOT NULL DEFAULT 'meetup',
            ADD COLUMN IF NOT EXISTS capacity INT,
            ADD COLUMN IF NOT EXISTS announced_at TIMESTAMPTZ
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_events_event_type ON events (event_type)")

    # 2. event_rsvps. Pre-existing 'attending' rows keep a NULL slot_range,
    #    which GiST exclusion ignores, so this cannot fail on live data.
    op.execute("ALTER TABLE event_rsvps ADD COLUMN IF NOT EXISTS slot_range INT4RANGE")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'no_double_booked_event_seats'
            ) THEN
                ALTER TABLE event_rsvps
                    ADD CONSTRAINT no_double_booked_event_seats EXCLUDE USING gist (
                        event_id WITH =,
                        slot_range WITH &&
                    ) WHERE (rsvp_status = 'attending');
            END IF;
        END $$
        """
    )

    # 3. scholarship_applications.
    op.execute(
        """
        ALTER TABLE scholarship_applications
            ADD COLUMN IF NOT EXISTS document_key VARCHAR(512),
            ADD COLUMN IF NOT EXISTS document_name VARCHAR(255)
        """
    )
    op.execute(
        """
        UPDATE scholarship_applications
           SET status = CASE status
                          WHEN 'pending'     THEN 'submitted'
                          WHEN 'shortlisted' THEN 'under_review'
                          WHEN 'awarded'     THEN 'approved'
                          ELSE status
                      END
         WHERE status IN ('pending', 'shortlisted', 'awarded')
        """
    )
    op.execute("ALTER TABLE scholarship_applications ALTER COLUMN status SET DEFAULT 'submitted'")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'ck_scholarship_applications_status'
            ) THEN
                ALTER TABLE scholarship_applications
                    DROP CONSTRAINT ck_scholarship_applications_status;
            END IF;
        END $$
        """
    )
    op.execute(
        """
        ALTER TABLE scholarship_applications
            ADD CONSTRAINT ck_scholarship_applications_status
                CHECK (status IN ('submitted', 'under_review', 'approved', 'rejected'))
        """
    )

    # 4. alumni_profiles.
    op.execute(
        "ALTER TABLE alumni_profiles ADD COLUMN IF NOT EXISTS is_visible BOOLEAN NOT NULL DEFAULT FALSE"
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'ck_alumni_profiles_membership'
            ) THEN
                ALTER TABLE alumni_profiles DROP CONSTRAINT ck_alumni_profiles_membership;
            END IF;
        END $$
        """
    )
    op.execute(
        """
        ALTER TABLE alumni_profiles
            ADD CONSTRAINT ck_alumni_profiles_membership
                CHECK (membership_status IN ('pending', 'active', 'expired', 'rejected'))
        """
    )


def downgrade() -> None:
    # Drop the exclusivity guard first, then the columns backing it.
    op.execute("ALTER TABLE event_rsvps DROP CONSTRAINT IF EXISTS no_double_booked_event_seats")
    op.execute("ALTER TABLE event_rsvps DROP COLUMN IF EXISTS slot_range")
    op.execute("DROP INDEX IF EXISTS ix_events_event_type")
    op.execute("ALTER TABLE events DROP COLUMN IF EXISTS announced_at")
    op.execute("ALTER TABLE events DROP COLUMN IF EXISTS capacity")
    op.execute("ALTER TABLE events DROP COLUMN IF EXISTS event_type")
    op.execute("ALTER TABLE scholarship_applications DROP COLUMN IF EXISTS document_name")
    op.execute("ALTER TABLE scholarship_applications DROP COLUMN IF EXISTS document_key")
    op.execute("ALTER TABLE alumni_profiles DROP COLUMN IF EXISTS is_visible")
    # NOTE: the status vocabulary is not mapped backwards on downgrade. Reverting
    # approved -> awarded would silently change review outcomes, so the new
    # vocabulary is intentionally left in place. Restore the legacy CHECK
    # manually if you truly need it.
