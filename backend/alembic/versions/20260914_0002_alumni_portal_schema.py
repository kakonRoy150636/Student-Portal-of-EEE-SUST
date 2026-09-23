"""alumni portal schema + booking approval columns

Revision ID: 20260914_0002
Revises: 20260911_0001
Create Date: 2026-09-14

Adds:
  * user_role enum value 'alumni'
  * alumni_profiles, events, event_rsvps, scholarships,
    scholarship_applications, mentorship_pairs, news_posts,
    gallery_albums, gallery_photos
  * room_reservations.approved_at / cancellation_* / rejection_reason
    (already referenced by the committed booking service)

Every statement is guarded with IF NOT EXISTS / DO $$ so the
migration is safe to re-run against a DB that was bootstrapped from
schema.sql without an alembic_version row.
"""
from alembic import op

revision = "20260914_0002"
down_revision = "20260911_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Stamp the empty 0001 revision if this DB was created from schema.sql
    # and never recorded an alembic_version row. Harmless if already present.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS alembic_version (
            version_num VARCHAR(32) NOT NULL,
            CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
        )
        """
    )

    # 1. Role enum — ADD VALUE cannot run inside a transaction on older PG,
    #    but PG 12+ (we ship 16) accepts it with IF NOT EXISTS.
    op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'alumni'")

    # 2. Booking-service columns that the live schema is missing.
    op.execute(
        """
        ALTER TABLE room_reservations
            ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS rejection_reason VARCHAR(255),
            ADD COLUMN IF NOT EXISTS cancelled_by UUID REFERENCES users(id),
            ADD COLUMN IF NOT EXISTS cancellation_reason VARCHAR(255),
            ADD COLUMN IF NOT EXISTS cancellation_at TIMESTAMPTZ
        """
    )

    # 3. Alumni profile (1:1 with users, unique on user_id).
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS alumni_profiles (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            batch_year INT NOT NULL,
            department VARCHAR(100) NOT NULL,
            graduation_date DATE NOT NULL,
            current_company VARCHAR(150),
            designation VARCHAR(150),
            industry VARCHAR(100),
            linkedin_url VARCHAR(255),
            verified_by_admin BOOLEAN NOT NULL DEFAULT FALSE,
            membership_status VARCHAR(20) NOT NULL DEFAULT 'pending',
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_alumni_profiles_user UNIQUE (user_id),
            CONSTRAINT ck_alumni_profiles_membership
                CHECK (membership_status IN ('pending', 'active', 'expired'))
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_alumni_profiles_user_id ON alumni_profiles (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_alumni_profiles_batch_year ON alumni_profiles (batch_year)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_alumni_profiles_industry ON alumni_profiles (industry)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_alumni_profiles_membership_status ON alumni_profiles (membership_status)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_alumni_profiles_batch_industry ON alumni_profiles (batch_year, industry)"
    )

    # 4. Events + RSVPs.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            created_by UUID NOT NULL REFERENCES users(id),
            title VARCHAR(200) NOT NULL,
            description VARCHAR(2000) NOT NULL,
            venue VARCHAR(200) NOT NULL,
            starts_at TIMESTAMPTZ NOT NULL,
            ends_at TIMESTAMPTZ NOT NULL,
            cover_photo_key VARCHAR(512),
            is_published BOOLEAN NOT NULL DEFAULT FALSE,
            members_only BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_events_starts_at ON events (starts_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_events_is_published ON events (is_published)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS event_rsvps (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            rsvp_status VARCHAR(20) NOT NULL DEFAULT 'attending',
            note VARCHAR(500),
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_event_rsvps_event_user UNIQUE (event_id, user_id),
            CONSTRAINT ck_event_rsvps_status
                CHECK (rsvp_status IN ('attending', 'interested', 'not_attending'))
        )
        """
    )

    # 5. Scholarships + applications.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS scholarships (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            created_by UUID NOT NULL REFERENCES users(id),
            title VARCHAR(200) NOT NULL,
            description VARCHAR(2000) NOT NULL,
            eligibility VARCHAR(1000) NOT NULL,
            amount_bdt INT,
            deadline DATE NOT NULL,
            application_target VARCHAR(255) NOT NULL,
            is_published BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_scholarships_deadline ON scholarships (deadline)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_scholarships_is_published ON scholarships (is_published)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS scholarship_applications (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            scholarship_id UUID NOT NULL REFERENCES scholarships(id) ON DELETE CASCADE,
            applicant_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            motivation VARCHAR(2000) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            reviewed_by UUID REFERENCES users(id),
            reviewed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_scholarship_applications UNIQUE (scholarship_id, applicant_id),
            CONSTRAINT ck_scholarship_applications_status
                CHECK (status IN ('pending', 'shortlisted', 'awarded', 'rejected'))
        )
        """
    )

    # 6. Mentorship.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS mentorship_pairs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            mentor_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            mentee_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            status VARCHAR(20) NOT NULL DEFAULT 'requested',
            requested_by UUID NOT NULL REFERENCES users(id),
            mentee_note VARCHAR(1000),
            mentor_note VARCHAR(1000),
            started_at TIMESTAMPTZ,
            ended_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_mentorship_pairs UNIQUE (mentor_id, mentee_id),
            CONSTRAINT ck_mentorship_pairs_status
                CHECK (status IN ('requested', 'active', 'ended')),
            CONSTRAINT ck_mentorship_pairs_not_self
                CHECK (mentor_id <> mentee_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_mentorship_pairs_mentee ON mentorship_pairs (mentee_id, status)"
    )

    # 7. News.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS news_posts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            author_id UUID NOT NULL REFERENCES users(id),
            title VARCHAR(200) NOT NULL,
            slug VARCHAR(220) NOT NULL UNIQUE,
            body VARCHAR(20000) NOT NULL,
            cover_photo_key VARCHAR(512),
            is_published BOOLEAN NOT NULL DEFAULT FALSE,
            published_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_news_posts_slug ON news_posts (slug)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_news_posts_is_published ON news_posts (is_published)")

    # 8. Gallery.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS gallery_albums (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            title VARCHAR(200) NOT NULL,
            description VARCHAR(1000),
            event_id UUID REFERENCES events(id) ON DELETE SET NULL,
            cover_photo_key VARCHAR(512),
            is_published BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS gallery_photos (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            album_id UUID NOT NULL REFERENCES gallery_albums(id) ON DELETE CASCADE,
            photo_key VARCHAR(512) NOT NULL,
            caption VARCHAR(500),
            sort_order INT NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS gallery_photos CASCADE")
    op.execute("DROP TABLE IF EXISTS gallery_albums CASCADE")
    op.execute("DROP TABLE IF EXISTS news_posts CASCADE")
    op.execute("DROP TABLE IF EXISTS mentorship_pairs CASCADE")
    op.execute("DROP TABLE IF EXISTS scholarship_applications CASCADE")
    op.execute("DROP TABLE IF EXISTS scholarships CASCADE")
    op.execute("DROP TABLE IF EXISTS event_rsvps CASCADE")
    op.execute("DROP TABLE IF EXISTS events CASCADE")
    op.execute("DROP TABLE IF EXISTS alumni_profiles CASCADE")
    # PostgreSQL cannot cheaply drop an enum value; leave 'alumni' in place.
    # Booking columns are left in place — they are additive and already used.
