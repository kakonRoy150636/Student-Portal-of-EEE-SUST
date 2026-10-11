"""Add course workspace announcements and read state.

Revision ID: 20261012_0012
Revises: 20261010_0011
"""

from alembic import op


revision = "20261012_0012"
down_revision = "20261010_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS course_announcements (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            offering_id UUID NOT NULL REFERENCES course_offerings(id) ON DELETE CASCADE,
            author_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            title VARCHAR(200) NOT NULL,
            body TEXT NOT NULL,
            announcement_type VARCHAR(30) NOT NULL DEFAULT 'general',
            status VARCHAR(20) NOT NULL DEFAULT 'draft',
            audience VARCHAR(30) NOT NULL DEFAULT 'enrolled_students',
            is_pinned BOOLEAN NOT NULL DEFAULT FALSE,
            publish_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            archived_at TIMESTAMPTZ,
            CONSTRAINT ck_course_announcements_type CHECK (
                announcement_type IN (
                    'general', 'class_update', 'class_cancelled', 'exam',
                    'assignment', 'urgent', 'resource', 'administrative'
                )
            ),
            CONSTRAINT ck_course_announcements_status CHECK (
                status IN ('draft', 'scheduled', 'published', 'archived')
            ),
            CONSTRAINT ck_course_announcements_audience CHECK (
                audience IN ('enrolled_students', 'cr_only', 'teachers_only')
            ),
            CONSTRAINT ck_course_announcements_lifecycle CHECK (
                (status != 'draft' OR publish_at IS NULL) AND
                (status NOT IN ('scheduled', 'published') OR publish_at IS NOT NULL) AND
                ((status = 'archived' AND archived_at IS NOT NULL AND is_pinned = false) OR
                 (status != 'archived' AND archived_at IS NULL))
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS announcement_reads (
            announcement_id UUID NOT NULL REFERENCES course_announcements(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            read_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT pk_announcement_reads PRIMARY KEY (announcement_id, user_id),
            CONSTRAINT uq_announcement_reads_announcement_user UNIQUE (announcement_id, user_id)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_course_announcements_offering_feed
            ON course_announcements (offering_id, status, publish_at, is_pinned)
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_course_announcements_offering_id ON course_announcements (offering_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_course_announcements_author_id ON course_announcements (author_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_course_announcements_due ON course_announcements (status, publish_at)")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_course_announcements_offering_created
            ON course_announcements (offering_id, created_at)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_announcement_reads_announcement_user_read
            ON announcement_reads (announcement_id, user_id, read_at)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_announcement_reads_user_read
            ON announcement_reads (user_id, read_at)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS course_resources (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            offering_id UUID NOT NULL REFERENCES course_offerings(id) ON DELETE CASCADE,
            resource_id UUID NOT NULL REFERENCES academic_resources(id) ON DELETE CASCADE,
            published_by UUID REFERENCES users(id) ON DELETE SET NULL,
            is_published BOOLEAN NOT NULL DEFAULT TRUE,
            archived_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_course_resources_offering_resource UNIQUE (offering_id, resource_id)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_course_resources_offering_state
            ON course_resources (offering_id, is_published, archived_at)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS course_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            offering_id UUID NOT NULL REFERENCES course_offerings(id) ON DELETE CASCADE,
            author_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            title VARCHAR(200) NOT NULL,
            description TEXT,
            event_type VARCHAR(30) NOT NULL DEFAULT 'other',
            starts_at TIMESTAMPTZ NOT NULL,
            ends_at TIMESTAMPTZ,
            location VARCHAR(200),
            reminder_minutes INTEGER,
            is_published BOOLEAN NOT NULL DEFAULT TRUE,
            archived_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT ck_course_events_type CHECK (event_type IN (
                'class', 'quiz', 'midterm', 'final', 'viva', 'assignment_deadline',
                'lab_exam', 'presentation', 'holiday', 'other'
            )),
            CONSTRAINT ck_course_events_reminder CHECK (
                reminder_minutes IS NULL OR reminder_minutes BETWEEN 0 AND 10080
            )
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_course_events_offering_start
            ON course_events (offering_id, starts_at, archived_at)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS course_questions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            offering_id UUID NOT NULL REFERENCES course_offerings(id) ON DELETE CASCADE,
            student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title VARCHAR(200) NOT NULL,
            body TEXT NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'open',
            visibility VARCHAR(20) NOT NULL DEFAULT 'course',
            answer_body TEXT,
            answered_by UUID REFERENCES users(id) ON DELETE SET NULL,
            answered_at TIMESTAMPTZ,
            resolved_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT ck_course_questions_status CHECK (status IN ('open', 'answered', 'resolved', 'closed')),
            CONSTRAINT ck_course_questions_visibility CHECK (visibility IN ('course', 'private'))
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_course_questions_offering_state
            ON course_questions (offering_id, status, created_at)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_course_questions_offering_state")
    op.execute("DROP TABLE IF EXISTS course_questions")
    op.execute("DROP INDEX IF EXISTS ix_course_events_offering_start")
    op.execute("DROP TABLE IF EXISTS course_events")
    op.execute("DROP INDEX IF EXISTS ix_course_resources_offering_state")
    op.execute("DROP TABLE IF EXISTS course_resources")
    op.execute("DROP INDEX IF EXISTS ix_announcement_reads_user_read")
    op.execute("DROP INDEX IF EXISTS ix_announcement_reads_announcement_user_read")
    op.execute("DROP INDEX IF EXISTS ix_course_announcements_offering_created")
    op.execute("DROP INDEX IF EXISTS ix_course_announcements_offering_feed")
    op.execute("DROP TABLE IF EXISTS announcement_reads")
    op.execute("DROP TABLE IF EXISTS course_announcements")
