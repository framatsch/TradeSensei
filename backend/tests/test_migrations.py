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

"""Tests for runtime database migration helpers."""

import subprocess
import uuid
from pathlib import Path

import pytest
from _pytest.monkeypatch import MonkeyPatch
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core import migrations
from app.core.config import settings


def test_build_migration_command_uses_project_paths() -> None:
    """Migration command should target the local venv and config file."""
    command = migrations._build_migration_command()

    assert Path(command[0]).name == "alembic"
    assert command[1] == "-c"
    assert Path(command[2]).name == "alembic.ini"
    assert command[3:] == ["upgrade", "head"]


def test_run_migrations_calls_upgrade(monkeypatch: MonkeyPatch) -> None:
    """Runtime migration helper should upgrade to the latest revision."""
    calls: list[tuple[list[str], Path, bool]] = []

    def fake_run(
        command: list[str], cwd: Path, check: bool, **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd, check))
        if "current" in command:
            return subprocess.CompletedProcess(command, 0, stdout="rev123 (head)\n")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(migrations.subprocess, "run", fake_run)

    migrations.run_migrations()

    # _get_current_revision calls fake_run twice, and the migration once
    # So length of calls should be 3
    assert len(calls) == 3
    assert calls[1][0][-2:] == ["upgrade", "head"]
    assert calls[1][1] == migrations.PROJECT_ROOT
    assert calls[1][2] is True


@pytest.mark.integration
def test_alembic_upgrade_and_downgrade_commands_succeed() -> None:
    """Migration scripts should apply and roll back cleanly."""
    backend_dir = Path(__file__).resolve().parents[1]

    def _skip_if_db_unavailable(result: subprocess.CompletedProcess[str]) -> None:
        if result.returncode != 0 and "Connect call failed" in result.stderr:
            pytest.skip("Database is unavailable for migration integration test.")

    upgrade = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        cwd=backend_dir,
        check=False,
    )
    _skip_if_db_unavailable(upgrade)
    assert upgrade.returncode == 0, upgrade.stderr

    downgrade = subprocess.run(
        ["uv", "run", "alembic", "downgrade", "-1"],
        capture_output=True,
        text=True,
        cwd=backend_dir,
        check=False,
    )
    _skip_if_db_unavailable(downgrade)
    if downgrade.returncode != 0:
        assert "Downgrade is not supported for b7e2c1d4f9a8" in downgrade.stderr
        pytest.skip("Head revision is intentionally non-downgradable.")

    reupgrade = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        cwd=backend_dir,
        check=False,
    )
    _skip_if_db_unavailable(reupgrade)
    assert reupgrade.returncode == 0, reupgrade.stderr


@pytest.mark.integration
@pytest.mark.asyncio
async def test_backfill_migration_seeds_defaults_for_existing_user() -> None:
    """Backfill migration should seed defaults for users created before it runs."""
    backend_dir = Path(__file__).resolve().parents[1]

    def _run_alembic(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["uv", "run", "alembic", *args],
            capture_output=True,
            text=True,
            cwd=backend_dir,
            check=False,
        )

    def _skip_if_db_unavailable(result: subprocess.CompletedProcess[str]) -> None:
        if result.returncode != 0 and "Connect call failed" in result.stderr:
            pytest.skip("Database is unavailable for migration integration test.")

    to_schema_only = _run_alembic("downgrade", "a7c3f61b9d20")
    _skip_if_db_unavailable(to_schema_only)
    if to_schema_only.returncode != 0:
        assert "Downgrade is not supported for b7e2c1d4f9a8" in to_schema_only.stderr
        pytest.skip("Cannot reach legacy revision from non-downgradable head.")

    user_id = uuid.uuid4()
    username = f"seedbackfill_{user_id.hex[:8]}"
    email = f"{username}@example.com"

    engine = create_async_engine(settings.async_database_url, echo=False)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    INSERT INTO users (
                        id,
                        username,
                        email,
                        hashed_password,
                        provider,
                        is_active,
                        refresh_token_version
                    )
                    VALUES (
                        :id,
                        :username,
                        :email,
                        :hashed_password,
                        'local',
                        true,
                        0
                    )
                    """
                ),
                {
                    "id": user_id,
                    "username": username,
                    "email": email,
                    "hashed_password": "test-hash",
                },
            )

        apply_seed = _run_alembic("upgrade", "c5d8e9f2a311")
        _skip_if_db_unavailable(apply_seed)
        assert apply_seed.returncode == 0, apply_seed.stderr

        async with engine.connect() as conn:
            field_count = await conn.scalar(
                text(
                    """
                    SELECT count(*)
                    FROM checkin_field_definitions
                    WHERE user_id = :user_id
                    """
                ),
                {"user_id": user_id},
            )
            phase_count = await conn.scalar(
                text(
                    """
                    SELECT count(*)
                    FROM market_phase_definitions
                    WHERE user_id = :user_id
                    """
                ),
                {"user_id": user_id},
            )
        assert field_count == 3
        assert phase_count == 4
    finally:
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
        await engine.dispose()

        restore_head = _run_alembic("upgrade", "head")
        _skip_if_db_unavailable(restore_head)
        assert restore_head.returncode == 0, restore_head.stderr
