"""Add offering publication, teacher requests and enrollment lifecycle fields.

Revision ID: 20261005_0010
Revises: 20261005_0009
"""
from alembic import op

revision = "20261005_0010"
down_revision = "20261005_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # There is no trustworthy creator/publication history in the old schema.
    # Preserve those offerings as drafts with an unknown creator, never infer
    # an administrator from the teacher coordinator or an arbitrary user.
    op.execute("""
        ALTER TABLE course_offerings
            ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES users(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS publication_status VARCHAR(20) NOT NULL DEFAULT 'draft',
            ADD COLUMN IF NOT EXISTS published_by UUID REFERENCES users(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    """)
    op.execute("ALTER TABLE course_offerings DROP CONSTRAINT IF EXISTS ck_course_offerings_publication_status")
    op.execute("""
        ALTER TABLE course_offerings ADD CONSTRAINT ck_course_offerings_publication_status
        CHECK (publication_status IN ('draft', 'published'))
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_course_offerings_semester_publication
        ON course_offerings (semester_id, publication_status)
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS teacher_assignment_requests (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            course_offering_id UUID NOT NULL REFERENCES course_offerings(id) ON DELETE CASCADE,
            teacher_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            decided_by UUID REFERENCES users(id) ON DELETE SET NULL,
            decided_at TIMESTAMPTZ,
            rejection_reason VARCHAR(1000),
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_teacher_assignment_requests_offering_teacher UNIQUE (course_offering_id, teacher_id),
            CONSTRAINT ck_teacher_assignment_requests_status CHECK (status IN ('pending', 'approved', 'rejected'))
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_teacher_assignment_requests_status_created
        ON teacher_assignment_requests (status, created_at)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_teacher_assignment_requests_teacher
        ON teacher_assignment_requests (teacher_id)
    """)

    # The existing full unique constraint includes dropped enrollments. Keep it
    # (and all IDs/FKs) so reselection has to update the original row, not insert
    # a second "active" row. No copied credits or advisor workflow is added.
    op.execute("""
        ALTER TABLE course_enrollments
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS dropped_at TIMESTAMPTZ
    """)
    op.execute("UPDATE course_enrollments SET updated_at = enrolled_at WHERE updated_at IS NULL")
    op.execute("""
        ALTER TABLE course_enrollments
            ALTER COLUMN updated_at SET DEFAULT CURRENT_TIMESTAMP,
            ALTER COLUMN updated_at SET NOT NULL
    """)
    # Invalid legacy statuses abort the transaction rather than silently
    # rewriting academic records; all four existing valid statuses survive.
    op.execute("ALTER TABLE course_enrollments DROP CONSTRAINT IF EXISTS ck_course_enrollments_status")
    op.execute("""
        ALTER TABLE course_enrollments ADD CONSTRAINT ck_course_enrollments_status
        CHECK (status IN ('enrolled', 'main', 'improvement', 'drop'))
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_course_enrollments_student_status
        ON course_enrollments (student_id, status)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_course_enrollments_student_status")
    op.execute("ALTER TABLE course_enrollments DROP CONSTRAINT IF EXISTS ck_course_enrollments_status")
    op.execute("ALTER TABLE course_enrollments DROP COLUMN IF EXISTS dropped_at")
    op.execute("ALTER TABLE course_enrollments DROP COLUMN IF EXISTS updated_at")
    op.execute("DROP TABLE IF EXISTS teacher_assignment_requests")
    op.execute("DROP INDEX IF EXISTS ix_course_offerings_semester_publication")
    op.execute("ALTER TABLE course_offerings DROP CONSTRAINT IF EXISTS ck_course_offerings_publication_status")
    op.execute("""
        ALTER TABLE course_offerings
            DROP COLUMN IF EXISTS updated_at,
            DROP COLUMN IF EXISTS created_at,
            DROP COLUMN IF EXISTS published_at,
            DROP COLUMN IF EXISTS published_by,
            DROP COLUMN IF EXISTS publication_status,
            DROP COLUMN IF EXISTS created_by
    """)
