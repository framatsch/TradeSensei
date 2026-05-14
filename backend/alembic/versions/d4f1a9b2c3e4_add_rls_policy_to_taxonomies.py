"""add rls policy to taxonomies

Revision ID: d4f1a9b2c3e4
Revises: b7e2c1d4f9a8
Create Date: 2026-05-12 07:05:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4f1a9b2c3e4"
down_revision: str | None = "b7e2c1d4f9a8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE taxonomies ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE taxonomies FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_policies
                WHERE schemaname = 'public'
                  AND tablename = 'taxonomies'
                  AND policyname = 'user_isolation'
            ) THEN
                CREATE POLICY user_isolation ON taxonomies
                USING (user_id = current_setting('app.current_user_id', true)::uuid);
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS user_isolation ON taxonomies")
    op.execute("ALTER TABLE taxonomies NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE taxonomies DISABLE ROW LEVEL SECURITY")
