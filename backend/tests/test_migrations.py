"""Tests for runtime database migration helpers."""

import subprocess
from pathlib import Path

import pytest
from _pytest.monkeypatch import MonkeyPatch

from app.core import migrations


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
    assert downgrade.returncode == 0, downgrade.stderr

    reupgrade = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        cwd=backend_dir,
        check=False,
    )
    _skip_if_db_unavailable(reupgrade)
    assert reupgrade.returncode == 0, reupgrade.stderr
