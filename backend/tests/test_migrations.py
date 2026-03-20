"""Tests for runtime database migration helpers."""

import subprocess
from pathlib import Path

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
        command: list[str], cwd: Path, check: bool
    ) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd, check))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(migrations.subprocess, "run", fake_run)

    migrations.run_migrations()

    assert len(calls) == 1
    assert calls[0][0][-2:] == ["upgrade", "head"]
    assert calls[0][1] == migrations.PROJECT_ROOT
    assert calls[0][2] is True
