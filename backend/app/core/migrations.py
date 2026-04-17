"""Helpers for applying Alembic migrations during application startup."""

import asyncio
import fcntl
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

MIGRATION_LOCK_FILE = Path("/tmp/tradesensei-alembic.lock")
"""Lock file used to serialize startup migrations across local processes."""

PROJECT_ROOT = Path(__file__).resolve().parents[2]
"""Backend project root that contains ``alembic.ini`` and the venv."""

ALEMBIC_BINARY = PROJECT_ROOT / ".venv" / "bin" / "alembic"
"""Alembic CLI executable inside the project virtual environment."""


def _build_migration_command() -> list[str]:
    """Create the Alembic CLI command used at runtime.

    Returns:
        The command line used to upgrade the database to ``head``.
    """
    return [
        str(ALEMBIC_BINARY),
        "-c",
        str(PROJECT_ROOT / "alembic.ini"),
        "upgrade",
        "head",
    ]


def run_migrations() -> None:
    """Apply all pending Alembic migrations to the configured database."""
    MIGRATION_LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with MIGRATION_LOCK_FILE.open("w", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        logger.info("Running database migrations")
        subprocess.run(
            _build_migration_command(),
            cwd=PROJECT_ROOT,
            check=True,
        )
        logger.info("Database migrations finished")
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


async def run_migrations_on_startup() -> None:
    """Run Alembic migrations without blocking the event loop."""
    await asyncio.to_thread(run_migrations)
