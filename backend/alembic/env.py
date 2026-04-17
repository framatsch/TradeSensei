"""Alembic environment configuration for async SQLAlchemy.

Uses the ``run_sync`` pattern so that the synchronous Alembic
``MigrationContext`` can operate against an async engine.

The database URL is **never** hard-coded in ``alembic.ini``.  Instead it
is read from the ``DATABASE_URL`` environment variable (or the app
``Settings`` object) at runtime, making the migration runner safe to use
in all environments without file edits.
"""

import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ── Import all models so that autogenerate can discover them ──────────────────
# isort: off
from app.core.database import Base  # noqa: F401
import app.models  # noqa: F401 — registers all models via __init__
# isort: on

# Alembic Config object — provides access to alembic.ini values.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Schemas owned by TimescaleDB that Alembic must never touch.
_EXCLUDED_SCHEMAS = frozenset(
    {
        "_timescaledb_catalog",
        "_timescaledb_internal",
        "_timescaledb_cache",
        "_timescaledb_config",
        "timescaledb_information",
    }
)


def include_object(
    object: object,  # noqa: A002
    name: str,
    type_: str,
    reflected: bool,
    compare_to: object,
) -> bool:
    """Exclude TimescaleDB internal tables from autogenerate diff.

    Args:
        object: The SQLAlchemy schema object being considered.
        name: The name of the object.
        type_: One of ``'table'``, ``'column'``, ``'index'``, etc.
        reflected: True if the object was reflected from the DB.
        compare_to: The model-side counterpart (may be None).

    Returns:
        True if the object should be included in the diff; False to skip.
    """
    if type_ == "table":
        schema = getattr(object, "schema", None)
        if schema in _EXCLUDED_SCHEMAS:
            return False
    return True


# ---------------------------------------------------------------------------
# Inject DATABASE_URL from environment so alembic.ini stays credential-free.
# ---------------------------------------------------------------------------
def _resolve_database_url() -> str:
    """Resolve database URL from environment.

    Resolution order:
    1) ``DATABASE_URL`` if explicitly provided.
    2) Build from ``DB_*`` parts (user/password/host/port/name).

    Returns:
        A SQLAlchemy async URL using the ``postgresql+asyncpg`` dialect.

    Raises:
        RuntimeError: If neither ``DATABASE_URL`` nor required DB parts are set.
    """
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        return db_url

    db_user = os.environ.get("DB_USER")
    db_password = os.environ.get("DB_PASSWORD")
    db_host = os.environ.get("DB_HOST", "db")
    db_port = os.environ.get("DB_PORT", "5432")
    db_name = os.environ.get("DB_NAME", "tradesensei")

    if not db_user or not db_password:
        raise RuntimeError(
            "Alembic database configuration missing. Set DATABASE_URL or both "
            "DB_USER and DB_PASSWORD (optionally DB_HOST/DB_PORT/DB_NAME)."
        )

    return f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


config.set_main_option("sqlalchemy.url", _resolve_database_url())


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine.
    Calls to ``context.execute()`` emit the given string to the script
    output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_schemas=True,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Execute migrations against the provided synchronous connection.

    Args:
        connection: A synchronous DBAPI connection wrapped by SQLAlchemy.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        include_schemas=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations via ``run_sync``."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode using an async engine."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
