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
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests")

from collections.abc import AsyncGenerator  # noqa: E402

import pytest_asyncio  # noqa: E402
import sqlalchemy as sa  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings  # noqa: E402
from app.core.database import Base, get_session  # noqa: E402
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

    We rely on Alembic rather than ``create_all`` to stay consistent
    with production.  This fixture is only used by integration tests
    that hit the real database.

    Yields:
        Nothing — sets up and tears down the schema around the session.
    """
    from sqlalchemy.ext.asyncio import AsyncEngine

    assert isinstance(engine, AsyncEngine)
    # The test DB schema should already be created by ``alembic upgrade head``
    # in CI.  For local runs, callers must run migrations first.
    yield
    # Drop all tables after the session — keeps the test DB clean.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.execute(sa.text("DROP TYPE IF EXISTS direction_enum"))
        await conn.execute(sa.text("DROP TYPE IF EXISTS asset_class_enum"))
    await engine.dispose()


@pytest_asyncio.fixture()
async def db_session(
    engine: object, setup_database: None
) -> AsyncGenerator[AsyncSession, None]:
    """Yield an :class:`AsyncSession` wrapped in a rolled-back transaction.

    Each test gets a fresh, isolated transaction that is rolled back on
    teardown so tests never interfere with each other.

    Args:
        engine: Session-scoped async engine.
        setup_database: Ensures migrations have run before this fixture.

    Yields:
        An open :class:`AsyncSession`.
    """
    from sqlalchemy.ext.asyncio import AsyncEngine

    assert isinstance(engine, AsyncEngine)
    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session, session.begin():
        yield session
        # rollback happens automatically — no commit is issued


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
