# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""enable_quick_notes_default_true

Revision ID: f3db6ff88b06
Revises: 9d38d119a8cf
Create Date: 2026-07-24 00:00:00.000000

Idempotent data migration: sets ``features['enable_quick_notes'] = true``
for all existing users so the new Quick Notes feature flag preserves current
behavior (the flag-reading convention treats a missing key as ``false``).

The flag is merged into the existing ``features`` JSON text — other flags are
never overwritten. Users without a ``features`` row in ``user_settings``
receive one containing only the new flag.

``downgrade()`` removes the key again (rows created by this migration revert
to an empty ``{}`` object, matching their previous effective state).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3db6ff88b06"
down_revision: str | None = "9d38d119a8cf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Merge the flag into existing features JSON (idempotent jsonb merge).
    op.execute(sa.text("UPDATE user_settings SET value = (value::jsonb || '{\"enable_quick_notes\": true}'::jsonb)::text WHERE key = 'features'"))
    # Users without a features row get one containing only the new flag.
    op.execute(
        sa.text(
            "INSERT INTO user_settings (id, user_id, key, value, created_at, updated_at) "
            "SELECT gen_random_uuid(), u.id, 'features', '{\"enable_quick_notes\": true}', now(), now() "
            "FROM users u "
            "WHERE NOT EXISTS ("
            "SELECT 1 FROM user_settings s WHERE s.user_id = u.id AND s.key = 'features'"
            ")"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("UPDATE user_settings SET value = (value::jsonb - 'enable_quick_notes')::text WHERE key = 'features'"))
