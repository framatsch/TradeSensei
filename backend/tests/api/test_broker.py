import uuid
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.api.v1.broker import _get_service, _get_service_public
from app.core.exceptions import AccountNotFoundError, ConfigurationError
from app.main import app
from app.models.account import Account

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_broker_service():
    mock = AsyncMock()
    return mock


@pytest.fixture
def override_broker_dependency(mock_broker_service):
    app.dependency_overrides[_get_service] = lambda: mock_broker_service
    app.dependency_overrides[_get_service_public] = lambda: mock_broker_service
    yield mock_broker_service
    app.dependency_overrides.clear()


async def test_schwab_callback_unauthenticated(
    override_broker_dependency
):
    """Callback route is reachable without a Bearer token and redirects."""
    mock_service = override_broker_dependency
    
    mock_account = Account()
    mock_account.id = uuid.uuid4()
    mock_service.complete_schwab_callback.return_value = mock_account

    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # No auth headers provided
        res = await client.get(
            "/api/v1/broker/schwab/callback",
            params={"code": "auth-code-123", "state": "state-456"}
        )
    
    assert res.status_code == 307
    assert "schwab_callback=success" in res.headers["location"]
    assert str(mock_account.id) in res.headers["location"]
    mock_service.complete_schwab_callback.assert_awaited_once_with(
        code="auth-code-123", state="state-456"
    )

async def test_schwab_callback_error_redirect(
    override_broker_dependency
):
    """Callback route redirects with error if missing params or exchange fails."""
    mock_service = override_broker_dependency
    
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Missing params
        res = await client.get("/api/v1/broker/schwab/callback")
        assert res.status_code == 307
        assert "schwab_callback=error" in res.headers["location"]

        # Exchange failure
        mock_service.complete_schwab_callback.side_effect = ConfigurationError("bad state")
        res2 = await client.get(
            "/api/v1/broker/schwab/callback",
            params={"code": "code", "state": "state"}
        )
        assert res2.status_code == 307
        assert "schwab_callback=error" in res2.headers["location"]
