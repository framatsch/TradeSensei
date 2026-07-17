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

"""consolidate_playbook_markdown_content

Revision ID: e8a7d3c91b42
Revises: d7e2f1a9c4b8
Create Date: 2026-07-17 08:40:00.000000

Legacy playbook ``description`` data is not recoverable after downgrade because
the old ``content_markdown`` source column is dropped during upgrade.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e8a7d3c91b42"
down_revision: str | None = "d7e2f1a9c4b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("UPDATE playbooks SET description = content_markdown"))
    op.drop_column("playbooks", "content_markdown")


def downgrade() -> None:
    op.add_column("playbooks", sa.Column("content_markdown", sa.Text(), nullable=True))
