"""Add optional semester target terms for scoped course offerings.

Revision ID: 20261010_0011
Revises: 20261005_0010
"""

from alembic import op


revision = "20261010_0011"
down_revision = "20261005_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE semesters
            ADD COLUMN IF NOT EXISTS target_term VARCHAR(4)
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'ck_semesters_target_term'
                  AND conrelid = 'semesters'::regclass
            ) THEN
                ALTER TABLE semesters
                    ADD CONSTRAINT ck_semesters_target_term
                    CHECK (
                        target_term IS NULL OR target_term IN
                        ('1-1', '1-2', '2-1', '2-2',
                         '3-1', '3-2', '4-1', '4-2')
                    );
            END IF;
        END $$
        """
    )
    # Only the canonical title form is authoritative. Historical titles such
    # as "Spring 2026" carry no reliable term mapping and remain legacy NULL.
    op.execute(
        """
        UPDATE semesters
        SET target_term = substring(title FROM '^Term ([1-4]-[12]), [0-9]{4}$')
        WHERE target_term IS NULL
          AND title ~ '^Term ([1-4]-[12]), [0-9]{4}$'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE semesters
            DROP CONSTRAINT IF EXISTS ck_semesters_target_term,
            DROP COLUMN IF EXISTS target_term
        """
    )
