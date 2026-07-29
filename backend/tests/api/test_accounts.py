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
from datetime import UTC
from typing import Any
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.api.v1.accounts import _get_broker_service, _get_service
from app.core.dependencies import require_portfolio_owner
from app.core.exceptions import AccountNotFoundError, ConfigurationError
from app.main import app
from app.schemas.account import (
    AccountMetrics,
    AccountRead,
)
from app.schemas.broker import BrokerConnectionTestResult
from app.schemas.common import CursorPage

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_account_service():
    mock = AsyncMock()
    return mock


@pytest.fixture
def mock_broker_service():
    mock = AsyncMock()
    return mock


@pytest.fixture
def override_account_dependency(mock_account_service, mock_broker_service):
    app.dependency_overrides[_get_service] = lambda: mock_account_service
    app.dependency_overrides[_get_broker_service] = lambda: mock_broker_service
    app.dependency_overrides[require_portfolio_owner] = lambda: None
    yield mock_account_service, mock_broker_service
    app.dependency_overrides.clear()


async def test_list_accounts(
    client: AsyncClient, primary_user: dict[str, Any], override_account_dependency
):
    mock_service, _ = override_account_dependency
    page = CursorPage(items=[], total=0, next_cursor=None)
    mock_service.list_accounts.return_value = page

    portfolio_id = str(uuid.uuid4())
    res = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/accounts",
        headers=primary_user["headers"],
    )
    assert res.status_code == 200, res.text


async def test_test_connection(
    client: AsyncClient, primary_user: dict[str, Any], override_account_dependency
):
    _, mock_broker = override_account_dependency
    mock_broker.test_connection.return_value = BrokerConnectionTestResult(
        success=True, message="OK"
    )

    portfolio_id = str(uuid.uuid4())
    res = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/accounts/test-connection",
        headers=primary_user["headers"],
        json={"type": "ibkr"},
    )
    assert res.status_code == 200, res.text

    mock_broker.test_connection.side_effect = AccountNotFoundError()
    res2 = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/accounts/test-connection",
        headers=primary_user["headers"],
        json={"type": "ibkr"},
    )
    assert res2.status_code == 404

    mock_broker.test_connection.side_effect = ConfigurationError("bad config")
    res3 = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/accounts/test-connection",
        headers=primary_user["headers"],
        json={"type": "ibkr"},
    )
    assert res3.status_code == 400


async def test_create_account(
    client: AsyncClient, primary_user: dict[str, Any], override_account_dependency
):
    mock_service, _ = override_account_dependency
    account_id = uuid.uuid4()
    from datetime import datetime
    mock_service.create_account.return_value = AccountRead(
        id=account_id,
        name="My Account",
        broker="IBKR",
        type="ibkr",
        currency="USD",
        portfolio_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    portfolio_id = str(uuid.uuid4())
    res = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/accounts",
        headers=primary_user["headers"],
        json={"name": "My Account", "type": "ibkr", "currency": "USD"},
    )
    assert res.status_code == 201, res.text


async def test_get_account_credentials(
    client: AsyncClient, primary_user: dict[str, Any], override_account_dependency
):
    mock_service, _ = override_account_dependency
    
    # Needs to return an AccountCredentialsRead
    # It has a base config
    mock_service.get_account_credentials.return_value = {"ibkr_endpoint": "x"}
    
    portfolio_id = str(uuid.uuid4())
    account_id = str(uuid.uuid4())
    
    res = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/accounts/{account_id}/credentials",
        headers=primary_user["headers"],
    )
    assert res.status_code == 200, res.text

    mock_service.get_account_credentials.side_effect = AccountNotFoundError()
    res2 = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/accounts/{account_id}/credentials",
        headers=primary_user["headers"],
    )
    assert res2.status_code == 404


async def test_get_account(
    client: AsyncClient, primary_user: dict[str, Any], override_account_dependency
):
    mock_service, _ = override_account_dependency
    
    from datetime import datetime
    mock_service.get_account.return_value = AccountRead(
        id=uuid.uuid4(),
        name="Test",
        broker="IBKR",
        type="ibkr",
        currency="USD",
        portfolio_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    
    portfolio_id = str(uuid.uuid4())
    account_id = str(uuid.uuid4())
    
    res = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/accounts/{account_id}",
        headers=primary_user["headers"],
    )
    assert res.status_code == 200, res.text

    mock_service.get_account.side_effect = AccountNotFoundError()
    res2 = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/accounts/{account_id}",
        headers=primary_user["headers"],
    )
    assert res2.status_code == 404


async def test_update_account(
    client: AsyncClient, primary_user: dict[str, Any], override_account_dependency
):
    mock_service, _ = override_account_dependency
    
    from datetime import datetime
    mock_service.update_account.return_value = AccountRead(
        id=uuid.uuid4(),
        name="Test",
        broker="IBKR",
        type="ibkr",
        currency="USD",
        portfolio_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    
    portfolio_id = str(uuid.uuid4())
    account_id = str(uuid.uuid4())
    
    res = await client.patch(
        f"/api/v1/portfolios/{portfolio_id}/accounts/{account_id}",
        headers=primary_user["headers"],
        json={"name": "New Name"},
    )
    assert res.status_code == 200, res.text

    mock_service.update_account.side_effect = AccountNotFoundError()
    res2 = await client.patch(
        f"/api/v1/portfolios/{portfolio_id}/accounts/{account_id}",
        headers=primary_user["headers"],
        json={"name": "New Name"},
    )
    assert res2.status_code == 404


async def test_delete_account(
    client: AsyncClient, primary_user: dict[str, Any], override_account_dependency
):
    mock_service, _ = override_account_dependency
    
    portfolio_id = str(uuid.uuid4())
    account_id = str(uuid.uuid4())
    
    res = await client.delete(
        f"/api/v1/portfolios/{portfolio_id}/accounts/{account_id}",
        headers=primary_user["headers"],
    )
    assert res.status_code == 204, res.text

    mock_service.delete_account.side_effect = AccountNotFoundError()
    res2 = await client.delete(
        f"/api/v1/portfolios/{portfolio_id}/accounts/{account_id}",
        headers=primary_user["headers"],
    )
    assert res2.status_code == 404


async def test_get_account_metrics(
    client: AsyncClient, primary_user: dict[str, Any], override_account_dependency
):
    mock_service, _ = override_account_dependency
    
    mock_service.get_metrics.return_value = AccountMetrics(
        total_dividends="0.00",
        total_withholding_tax="0.00",
    )
    
    portfolio_id = str(uuid.uuid4())
    account_id = str(uuid.uuid4())
    
    res = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/accounts/{account_id}/metrics",
        headers=primary_user["headers"],
    )
    assert res.status_code == 200, res.text

    mock_service.get_metrics.side_effect = AccountNotFoundError()
    res2 = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/accounts/{account_id}/metrics",
        headers=primary_user["headers"],
    )
    assert res2.status_code == 404
