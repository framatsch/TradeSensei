"""Shared pytest fixtures for unit and integration tests.

Fixtures defined here are available to all test modules automatically.
The integration fixtures (``db_session``, ``client``) require a live
TimescaleDB instance reachable via the ``DATABASE_URL`` environment
variable.

Environment variables are seeded with test defaults before any app module
is imported, so unit tests can run without a real database.
"""

import os

# Seed required env vars before any app module is imported.
# CI overrides DATABASE_URL via the workflow env block.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@localhost:5432/test_tradejournal",
)
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-minimum-32chars")

from collections.abc import AsyncGenerator  # noqa: E402

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncConnection,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings  # noqa: E402
from app.core.database import get_session  # noqa: E402
from app.main import app  # noqa: E402


@pytest_asyncio.fixture(scope="session")
async def engine() -> AsyncGenerator[object, None]:
    """Create a test async engine scoped to the entire test session.

    Yields:
        An :class:`AsyncEngine` connected to the test database.
    """
    test_engine = create_async_engine(settings.database_url, echo=False)
    yield test_engine
    await test_engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def setup_database(engine: object) -> AsyncGenerator[None, None]:
    """Run Alembic migrations once before the test session starts.

    Applies ``alembic upgrade head`` at session startup so the schema is
    always current regardless of the prior state of the test database.
    Does *not* drop tables on teardown — per-test isolation is handled by
    the savepoint-based rollback in :func:`db_connection`.

    Yields:
        Nothing — ensures the schema is up to date before any test runs.
    """
    import subprocess
    from pathlib import Path

    from sqlalchemy.ext.asyncio import AsyncEngine

    assert isinstance(engine, AsyncEngine)

    # Apply migrations using the venv's alembic binary so DATABASE_URL and
    # SECRET_KEY (inherited from the current environment) are used.
    backend_dir = Path(__file__).parent.parent
    alembic_bin = backend_dir / ".venv" / "bin" / "alembic"
    subprocess.run(
        [str(alembic_bin), "upgrade", "head"],
        check=True,
        capture_output=True,
        cwd=str(backend_dir),
        env=os.environ.copy(),
    )

    yield
    # No teardown — leave tables in place so the next test run can reuse them.


@pytest_asyncio.fixture()
async def db_connection(
    engine: object, setup_database: None
) -> AsyncGenerator[AsyncConnection, None]:
    """Yield an :class:`AsyncConnection` with an open transaction.

    The transaction is rolled back on teardown so every test starts with
    a clean slate.  All :class:`AsyncSession` instances created from this
    connection automatically participate in the same transaction via the
    ``join_transaction_mode="create_savepoint"`` option, which lets
    service-layer ``commit()`` calls succeed without permanently writing
    data.

    Args:
        engine: Session-scoped async engine.
        setup_database: Ensures migrations have run before this fixture.

    Yields:
        An open :class:`AsyncConnection` inside a rolled-back transaction.
    """
    from sqlalchemy.ext.asyncio import AsyncEngine

    assert isinstance(engine, AsyncEngine)
    async with engine.connect() as conn:
        await conn.begin()
        yield conn
        await conn.rollback()


@pytest_asyncio.fixture()
async def db_session(
    db_connection: AsyncConnection,
) -> AsyncGenerator[AsyncSession, None]:
    """Yield an :class:`AsyncSession` bound to the test connection.

    The session uses ``join_transaction_mode="create_savepoint"`` so that
    service-layer ``commit()`` calls create/release savepoints rather than
    committing the outer transaction.  The outer transaction is rolled back
    by :func:`db_connection` after each test.

    Args:
        db_connection: The per-test connection with an open transaction.

    Yields:
        An open :class:`AsyncSession`.
    """
    session_factory = async_sessionmaker(
        bind=db_connection,
        class_=AsyncSession,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture()
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Yield an HTTPX ``AsyncClient`` wired to the FastAPI test app.

    Overrides the ``get_session`` dependency so every request uses the
    same rolled-back test transaction.

    Args:
        db_session: The test session fixture.

    Yields:
        An :class:`AsyncClient` targeting the test application.
    """

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
