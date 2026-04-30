"""Shared pytest fixtures for unit and integration tests.

Fixtures defined here are available to all test modules automatically.
The integration fixtures (``db_session``, ``client``) require a live
TimescaleDB instance reachable via the ``DATABASE_URL`` environment
variable.

Environment variables are seeded with test defaults before any app module
is imported, so unit tests can run without a real database.
"""

import os
import uuid as _uuid

# Seed required env vars before any app module is imported.
# CI overrides DATABASE_URL via the workflow env block.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://tradesensei:tradesensei@localhost:5433/test_tradesensei",
)
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-minimum-32chars")
os.environ.setdefault("UPLOAD_DIR", "./uploads")

from collections.abc import AsyncGenerator  # noqa: E402
from typing import Any  # noqa: E402
from unittest.mock import AsyncMock, MagicMock  # noqa: E402

import pytest  # noqa: E402
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


@pytest.fixture()
def mock_session() -> AsyncMock:
    """Return a mock :class:`AsyncSession` for use in unit tests.

    This fixture is shared across all service unit tests so that each
    test file does not need to define its own identical copy.

    Returns:
        A fresh :class:`AsyncMock` standing in for the SQLAlchemy session.
    """
    session = AsyncMock()
    session.add = MagicMock()
    session.delete = MagicMock()
    return session


@pytest_asyncio.fixture(scope="session")
async def engine() -> AsyncGenerator[object]:
    """Create a test async engine scoped to the entire test session.

    Yields:
        An :class:`AsyncEngine` connected to the test database.
    """
    test_engine = create_async_engine(settings.async_database_url, echo=False)
    yield test_engine
    await test_engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def setup_database(engine: object) -> AsyncGenerator[None]:
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

    # Apply migrations using the current environment's alembic
    import sys

    backend_dir = Path(__file__).parent.parent
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
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
) -> AsyncGenerator[AsyncConnection]:
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
) -> AsyncGenerator[AsyncSession]:
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
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    """Yield an HTTPX ``AsyncClient`` wired to the FastAPI test app.

    Overrides the ``get_session`` dependency so every request uses the
    same rolled-back test transaction.

    Args:
        db_session: The test session fixture.

    Yields:
        An :class:`AsyncClient` targeting the test application.
    """

    async def override_get_session() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="https://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Ownership test helpers
# ---------------------------------------------------------------------------

_REGISTER_URL = "/api/v1/auth/register"
_TOKEN_URL = "/api/v1/auth/token"


async def _register_and_login(
    client: AsyncClient, *, username: str, email: str, password: str
) -> dict[str, Any]:
    """Register a user and return a dict with ``headers`` and ``user_id``.

    Args:
        client: The test HTTP client.
        username: Unique username.
        email: Unique email.
        password: Plain-text password.

    Returns:
        Dict with ``headers`` (Bearer auth) and ``user_id`` (str UUID).
    """
    reg = await client.post(
        _REGISTER_URL,
        json={"username": username, "email": email, "password": password},
    )
    assert reg.status_code == 201, reg.text
    user_id: str = reg.json()["data"]["id"]

    tok = await client.post(
        _TOKEN_URL,
        data={"username": username, "password": password},
    )
    assert tok.status_code == 200, tok.text
    access_token: str = tok.json()["access_token"]
    return {"headers": {"Authorization": f"Bearer {access_token}"}, "user_id": user_id}


@pytest_asyncio.fixture()
async def primary_user(client: AsyncClient) -> dict[str, Any]:
    """Register + login a primary test user; return headers + user_id.

    Used by ownership tests as the resource owner.

    Returns:
        Dict with ``headers`` (Bearer auth header dict) and ``user_id`` (str).
    """
    uid = str(_uuid.uuid4())[:8]
    return await _register_and_login(
        client,
        username=f"owner_{uid}",
        email=f"owner_{uid}@example.com",
        password="OwnerP@ss99!",
    )


@pytest_asyncio.fixture()
async def other_user(client: AsyncClient) -> dict[str, Any]:
    """Register + login a second test user; return headers + user_id.

    Used by ownership tests as the attacker / unauthorised requester.

    Returns:
        Dict with ``headers`` (Bearer auth header dict) and ``user_id`` (str).
    """
    uid = str(_uuid.uuid4())[:8]
    return await _register_and_login(
        client,
        username=f"other_{uid}",
        email=f"other_{uid}@example.com",
        password="OtherP@ss99!",
    )


@pytest_asyncio.fixture()
async def other_users_account(
    client: AsyncClient, other_user: dict[str, Any]
) -> dict[str, Any]:
    """Create an account owned by ``other_user``; return its data dict.

    Args:
        client: The test HTTP client.
        other_user: The other_user fixture dict.

    Returns:
        The account ``data`` dict from the 201 response.
    """
    p_resp = await client.post(
        "/api/v1/portfolios",
        json={"name": "Other Portfolio", "base_currency": "USD"},
        headers=other_user["headers"],
    )
    assert p_resp.status_code == 201, p_resp.text
    portfolio_id = p_resp.json()["data"]["id"]

    resp = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/accounts",
        json={"name": "Other Account", "type": "manual", "currency": "USD"},
        headers=other_user["headers"],
    )
    assert resp.status_code == 201, resp.text
    data = dict(resp.json()["data"])
    data["portfolio_id"] = portfolio_id
    return data


@pytest_asyncio.fixture()
async def other_users_trade(
    client: AsyncClient,
    other_user: dict[str, Any],
    other_users_account: dict[str, Any],
) -> dict[str, Any]:
    """Create a trade owned by ``other_user``; return its data dict.

    Args:
        client: The test HTTP client.
        other_user: The other_user fixture dict.
        other_users_account: Account belonging to other_user.

    Returns:
        The trade ``data`` dict from the 201 response.
    """
    resp = await client.post(
        f"/api/v1/portfolios/{other_users_account['portfolio_id']}/trades",
        json={
            "account_id": other_users_account["id"],
            "symbol": "OTH",
            "direction": "LONG",
            "asset_class": "EQUITY",
            "quantity": "1",
            "entry_price": "10",
            "opened_at": "2024-01-15T10:00:00Z",
            "currency": "USD",
        },
        headers=other_user["headers"],
    )
    assert resp.status_code == 201, resp.text
    data = dict(resp.json()["data"])
    data["portfolio_id"] = other_users_account["portfolio_id"]
    return data


@pytest_asyncio.fixture()
async def other_users_playbook(
    client: AsyncClient, other_user: dict[str, Any]
) -> dict[str, Any]:
    """Create a playbook owned by ``other_user``; return its data dict.

    Args:
        client: The test HTTP client.
        other_user: The other_user fixture dict.

    Returns:
        The playbook ``data`` dict from the 201 response.
    """
    resp = await client.post(
        "/api/v1/playbooks",
        json={"name": "Other Playbook", "description": "attacker playbook"},
        headers=other_user["headers"],
    )
    assert resp.status_code == 201, resp.text
    return dict(resp.json()["data"])


@pytest_asyncio.fixture()
async def other_users_tag(
    client: AsyncClient, other_user: dict[str, Any]
) -> dict[str, Any]:
    """Create a tag owned by ``other_user``; return its data dict.

    Args:
        client: The test HTTP client.
        other_user: The other_user fixture dict.

    Returns:
        The tag ``data`` dict from the 201 response.
    """
    resp = await client.post(
        "/api/v1/tags",
        json={"name": "other-tag", "color": "#FF0000"},
        headers=other_user["headers"],
    )
    assert resp.status_code == 201, resp.text
    return dict(resp.json()["data"])


@pytest_asyncio.fixture()
async def other_users_note(
    client: AsyncClient,
    other_user: dict[str, Any],
    other_users_trade: dict[str, Any],
) -> dict[str, Any]:
    """Create a trade note owned by ``other_user``; return its data dict.

    Args:
        client: The test HTTP client.
        other_user: The other_user fixture dict.
        other_users_trade: Trade belonging to other_user.

    Returns:
        The note ``data`` dict from the 201 response.
    """
    trade_id = other_users_trade["id"]
    resp = await client.post(
        f"/api/v1/trades/{trade_id}/notes",
        json={"content": "attacker note"},
        headers=other_user["headers"],
    )
    assert resp.status_code == 201, resp.text
    return dict(resp.json()["data"])


@pytest_asyncio.fixture()
async def other_users_execution(
    client: AsyncClient,
    other_user: dict[str, Any],
    other_users_trade: dict[str, Any],
    other_users_account: dict[str, Any],
) -> dict[str, Any]:
    """Create a manual execution owned by ``other_user``; return its data dict.

    Adds a manual execution leg to other_user's trade so that ownership
    tests for the execution endpoints can assert cross-user access is
    rejected.

    Args:
        client: The test HTTP client.
        other_user: The other_user fixture dict.
        other_users_trade: Trade belonging to other_user.

    Returns:
        The execution ``data`` dict from the 201 response.
    """
    trade_id = other_users_trade["id"]
    resp = await client.post(
        f"/api/v1/portfolios/{other_users_account['portfolio_id']}/trades/{trade_id}/executions",
        json={
            "quantity": "1",
            "price": "10",
            "executed_at": "2024-01-16T10:00:00Z",
            "direction": "LONG",
            "commission": "0",
        },
        headers=other_user["headers"],
    )
    assert resp.status_code == 201, resp.text
    data = dict(resp.json()["data"])
    data["portfolio_id"] = other_users_account["portfolio_id"]
    return data
