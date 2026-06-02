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

import logging
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e6c9b3f1a2d0"
down_revision: str | None = "314159265358"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

logger = logging.getLogger("alembic.runtime.migration")


def _escape_sql(value: str) -> str:
    return value.replace("'", "''")


def _get_storage_public_url() -> str:
    """Read STORAGE_PUBLIC_URL from app settings (same source as the runtime app)."""
    try:
        from app.core.config import settings

        return (settings.storage_public_url or "").rstrip("/")
    except Exception:
        import os

        return os.getenv("STORAGE_PUBLIC_URL", "").rstrip("/")


def upgrade() -> None:
    storage_public_url = _get_storage_public_url()
    if not storage_public_url:
        logger.warning(
            "STORAGE_PUBLIC_URL is not set — migration e6c9b3f1a2d0 skipped the URL backfill. "
            "Existing rows with full public URLs will NOT be converted to bucket/key references. "
            "Run this migration again after setting STORAGE_PUBLIC_URL to backfill correctly."
        )
        return

    prefix = _escape_sql(f"{storage_public_url}/")
    prefix_len = len(f"{storage_public_url}/")

    op.execute(
        sa.text(
            "UPDATE daily_checkins "
            "SET screenshot_urls = ("
            "SELECT COALESCE(array_agg(CASE "
            "WHEN url = '' THEN url "
            f"WHEN left(url, {prefix_len}) = '{prefix}' THEN substr(url, {prefix_len + 1}) "
            "ELSE url END), ARRAY[]::text[]) "
            "FROM unnest(COALESCE(daily_checkins.screenshot_urls, ARRAY[]::text[])) AS x(url)"
            ")"
        )
    )

    op.execute(
        sa.text(
            "UPDATE trades "
            "SET image_urls = ("
            "SELECT COALESCE(jsonb_agg(CASE "
            "WHEN url = '' THEN url "
            f"WHEN left(url, {prefix_len}) = '{prefix}' THEN substr(url, {prefix_len + 1}) "
            "ELSE url END), '[]'::jsonb) "
            "FROM jsonb_array_elements_text(COALESCE(trades.image_urls, '[]'::jsonb)) AS x(url)"
            ")"
        )
    )

    op.execute(
        sa.text(
            "UPDATE playbook_attachments "
            "SET storage_url = CASE "
            "WHEN storage_url IS NULL OR storage_url = '' THEN storage_url "
            f"WHEN left(storage_url, {prefix_len}) = '{prefix}' THEN substr(storage_url, {prefix_len + 1}) "
            "ELSE storage_url END"
        )
    )


def downgrade() -> None:
    storage_public_url = _get_storage_public_url()
    if not storage_public_url:
        logger.warning(
            "STORAGE_PUBLIC_URL is not set — migration e6c9b3f1a2d0 skipped the URL downgrade backfill. "
            "Existing rows with bucket/key references will NOT be reconstructed to full public URLs."
        )
        return

    base = _escape_sql(storage_public_url)

    op.execute(
        sa.text(
            "UPDATE daily_checkins "
            "SET screenshot_urls = ("
            "SELECT COALESCE(array_agg(CASE "
            "WHEN url = '' THEN url "
            "WHEN position('://' in url) > 0 THEN url "
            f"ELSE '{base}/' || url END), ARRAY[]::text[]) "
            "FROM unnest(COALESCE(daily_checkins.screenshot_urls, ARRAY[]::text[])) AS x(url)"
            ")"
        )
    )

    op.execute(
        sa.text(
            "UPDATE trades "
            "SET image_urls = ("
            "SELECT COALESCE(jsonb_agg(CASE "
            "WHEN url = '' THEN url "
            "WHEN position('://' in url) > 0 THEN url "
            f"ELSE '{base}/' || url END), '[]'::jsonb) "
            "FROM jsonb_array_elements_text(COALESCE(trades.image_urls, '[]'::jsonb)) AS x(url)"
            ")"
        )
    )

    op.execute(
        sa.text(
            "UPDATE playbook_attachments "
            "SET storage_url = CASE "
            "WHEN storage_url IS NULL OR storage_url = '' THEN storage_url "
            "WHEN position('://' in storage_url) > 0 THEN storage_url "
            f"ELSE '{base}/' || storage_url END"
        )
    )
