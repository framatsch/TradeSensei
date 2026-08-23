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

import uuid
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.api.v1.broker import _get_service, _get_service_public
from app.core.exceptions import ConfigurationError, UpstreamServiceUnavailableError
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
    """Callback route is reachable without a Bearer token and returns HTML."""
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
    
    assert res.status_code == 200
    assert "Authorization successful" in res.text
    mock_service.complete_schwab_callback.assert_awaited_once_with(
        code="auth-code-123", state="state-456"
    )

async def test_schwab_callback_error_redirect(
    override_broker_dependency
):
    """Callback route returns HTML errors for invalid/missing callback params."""
    mock_service = override_broker_dependency
    
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Missing params
        res = await client.get("/api/v1/broker/schwab/callback")
        assert res.status_code == 400
        assert "Missing code or state" in res.text

        # Exchange failure
        mock_service.complete_schwab_callback.side_effect = ConfigurationError("bad state")
        res2 = await client.get(
            "/api/v1/broker/schwab/callback",
            params={"code": "code", "state": "state"}
        )
        assert res2.status_code == 500
        assert "Authorization failed" in res2.text


async def test_sync_account_upstream_unavailable_returns_503(
    client: AsyncClient,
    primary_user: dict[str, object],
    override_broker_dependency,
):
    mock_service = override_broker_dependency
    mock_service.sync_account.side_effect = UpstreamServiceUnavailableError(
        "IBKR Flex API temporarily unavailable"
    )

    account_id = uuid.uuid4()
    res = await client.post(
        f"/api/v1/broker/sync/{account_id}",
        headers=primary_user["headers"],  # type: ignore[arg-type]
    )

    assert res.status_code == 503
    assert "temporarily unavailable" in res.json()["detail"]
