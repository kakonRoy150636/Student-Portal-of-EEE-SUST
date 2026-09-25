-- Alumni portal ORM/DB parity (matches backend/app/models/alumni.py).
--
-- The models declared columns that schema.sql and alembic 0002 never created,
-- so any insert/select touching them would fail with UndefinedColumn. This
-- migration brings the database up to the models. Idempotent and additive:
-- re-running it on an already-patched database is a no-op.
--
-- One data migration is included: scholarship_applications.status used to
-- default to 'pending' with the vocabulary
--   (pending | shortlisted | awarded | rejected)
-- while the model expects
--   (submitted | under_review | approved | rejected).
-- The legacy values are mapped onto the new vocabulary before the CHECK
-- constraint is replaced.

-- 1. events: type / capacity / announced_at -------------------------------
ALTER TABLE events
    ADD COLUMN IF NOT EXISTS event_type VARCHAR(20) NOT NULL DEFAULT 'meetup',
    ADD COLUMN IF NOT EXISTS capacity INT,
    ADD COLUMN IF NOT EXISTS announced_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS ix_events_event_type ON events (event_type);

-- 2. event_rsvps: slot_range + overbooking guard ---------------------------
ALTER TABLE event_rsvps
    ADD COLUMN IF NOT EXISTS slot_range INT4RANGE;

-- Existing 'attending' rows have no seat assigned yet, so they carry a NULL
-- slot and consume no capacity. New RSVPs assign their own seat in the app
-- layer. A NULL slot_range is ignored by GiST exclusion, so adding the
-- constraint cannot fail on pre-existing data.
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
END $$;

-- 3. scholarship_applications: document columns + status vocabulary -------
ALTER TABLE scholarship_applications
    ADD COLUMN IF NOT EXISTS document_key VARCHAR(512),
    ADD COLUMN IF NOT EXISTS document_name VARCHAR(255);

-- Map legacy statuses onto the model vocabulary before the CHECK is swapped.
UPDATE scholarship_applications
   SET status = CASE status
                  WHEN 'pending'     THEN 'submitted'
                  WHEN 'shortlisted' THEN 'under_review'
                  WHEN 'awarded'     THEN 'approved'
                  ELSE status
              END
 WHERE status IN ('pending', 'shortlisted', 'awarded');

ALTER TABLE scholarship_applications
    ALTER COLUMN status SET DEFAULT 'submitted';

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ck_scholarship_applications_status'
    ) THEN
        ALTER TABLE scholarship_applications
            DROP CONSTRAINT ck_scholarship_applications_status;
    END IF;
END $$;

ALTER TABLE scholarship_applications
    ADD CONSTRAINT ck_scholarship_applications_status
        CHECK (status IN ('submitted', 'under_review', 'approved', 'rejected'));

-- 4. alumni_profiles: is_visible + rejected membership status -------------
ALTER TABLE alumni_profiles
    ADD COLUMN IF NOT EXISTS is_visible BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS ix_alumni_profiles_is_visible ON alumni_profiles (is_visible);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ck_alumni_profiles_membership'
    ) THEN
        ALTER TABLE alumni_profiles DROP CONSTRAINT ck_alumni_profiles_membership;
    END IF;
END $$;

ALTER TABLE alumni_profiles
    ADD CONSTRAINT ck_alumni_profiles_membership
        CHECK (membership_status IN ('pending', 'active', 'expired', 'rejected'));
