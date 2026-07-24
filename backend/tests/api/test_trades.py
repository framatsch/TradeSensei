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
from app.core.dependencies import require_portfolio_owner
from typing import Any
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.api.v1.trades import _get_service
from app.core.deps import get_session_with_rls
from app.core.exceptions import ConfigurationError, UnsupportedContentTypeError, TradeNotFoundError

from app.schemas.trade import TradeRead
from app.models.trade import AssetClass, Direction
from app.schemas.common import CursorPage

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_service():
    mock = AsyncMock()
    return mock

@pytest.fixture
def override_dependency(mock_service):
    from app.main import app
    app.dependency_overrides[_get_service] = lambda: mock_service
    app.dependency_overrides[require_portfolio_owner] = lambda: None
    app.dependency_overrides[get_session_with_rls] = lambda: AsyncMock()
    yield mock_service
    app.dependency_overrides.clear()

def get_mock_trade(portfolio_id, user_id, trade_id):
    return TradeRead(
        id=trade_id,
        account_id=None,
        portfolio_id=portfolio_id,
        symbol="AAPL",
        direction=Direction.LONG,
        asset_class=AssetClass.EQUITY,
        is_combo=False,
        quantity=Decimal("1"),
        entry_price=Decimal("100.0"),
        exit_price=None,
        stop_loss=None,
        take_profit=None,
        opened_at=datetime.now(timezone.utc),
        closed_at=None,
        pnl=None,
        net_pnl=None,
        commission=Decimal("0.0"),
        journal=None,
        user_rating=None,
        tradingview_link=None,
        image_urls=[],
        currency="USD",
        pnl_eur=None,
        net_pnl_eur=None,
        playbook_id=None,
        playbook_name=None,
        account_name=None,
        account_type=None,
        taxonomies=[],
        annotations=[],
        trade_notes=[],
        legs=[],
        is_manually_edited=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

async def test_get_trade_image_upload_url(client: AsyncClient, primary_user: dict[str, Any]):
    with patch("app.api.v1.trades.StorageService") as mock_storage:
        mock_instance = mock_storage.return_value
        mock_instance.generate_trade_image_upload_url.return_value = ("http://presigned", "mykey")
        
        response = await client.post(
            "/api/v1/trades/upload-url",
            json={"filename": "test.png", "content_type": "image/png"},
            headers=primary_user["headers"]
        )
        assert response.status_code == 200

        mock_instance.generate_trade_image_upload_url.side_effect = UnsupportedContentTypeError("Bad type")
        response = await client.post(
            "/api/v1/trades/upload-url",
            json={"filename": "test.txt", "content_type": "text/plain"},
            headers=primary_user["headers"]
        )
        assert response.status_code == 422

        mock_instance.generate_trade_image_upload_url.side_effect = ConfigurationError("No storage")
        response = await client.post(
            "/api/v1/trades/upload-url",
            json={"filename": "test.png", "content_type": "image/png"},
            headers=primary_user["headers"]
        )
        assert response.status_code == 503

async def test_bulk_delete_trades(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    portfolio_id = uuid.uuid4()
    trade_id = uuid.uuid4()
    
    override_dependency.bulk_delete_trades.return_value = 1
    
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades/bulk/delete",
        json={"trade_ids": [str(trade_id)]},
        headers=primary_user["headers"]
    )
    assert response.status_code == 200

async def test_bulk_assign_taxonomies(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    portfolio_id = uuid.uuid4()
    
    override_dependency.bulk_assign_taxonomies.return_value = 1
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades/bulk/assign-taxonomies",
        json={"trade_ids": [str(uuid.uuid4())], "taxonomy_ids": [str(uuid.uuid4())], "mode": "add"},
        headers=primary_user["headers"]
    )
    assert response.status_code == 200

    override_dependency.bulk_assign_taxonomies.side_effect = ValueError("Not found")
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades/bulk/assign-taxonomies",
        json={"trade_ids": [str(uuid.uuid4())], "taxonomy_ids": [str(uuid.uuid4())], "mode": "add"},
        headers=primary_user["headers"]
    )
    assert response.status_code == 404

    override_dependency.bulk_assign_taxonomies.side_effect = PermissionError("Not allowed")
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades/bulk/assign-taxonomies",
        json={"trade_ids": [str(uuid.uuid4())], "taxonomy_ids": [str(uuid.uuid4())], "mode": "add"},
        headers=primary_user["headers"]
    )
    assert response.status_code == 403

async def test_bulk_assign_playbook(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    portfolio_id = uuid.uuid4()
    
    override_dependency.bulk_assign_playbook.return_value = 1
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades/bulk/assign-playbook",
        json={"trade_ids": [str(uuid.uuid4())], "playbook_id": str(uuid.uuid4())},
        headers=primary_user["headers"]
    )
    assert response.status_code == 200

    override_dependency.bulk_assign_playbook.side_effect = ValueError("Not found")
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades/bulk/assign-playbook",
        json={"trade_ids": [str(uuid.uuid4())], "playbook_id": str(uuid.uuid4())},
        headers=primary_user["headers"]
    )
    assert response.status_code == 404

    override_dependency.bulk_assign_playbook.side_effect = PermissionError("Not allowed")
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades/bulk/assign-playbook",
        json={"trade_ids": [str(uuid.uuid4())], "playbook_id": str(uuid.uuid4())},
        headers=primary_user["headers"]
    )
    assert response.status_code == 403

async def test_list_trades(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    portfolio_id = uuid.uuid4()
    mock_trade = get_mock_trade(portfolio_id, primary_user["user_id"], uuid.uuid4())
    
    override_dependency.list_trades.return_value = CursorPage(items=[mock_trade], next_cursor=None, has_next=False, total=1)
    
    response = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        headers=primary_user["headers"]
    )
    assert response.status_code == 200

async def test_get_trade(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    portfolio_id = uuid.uuid4()
    trade_id = uuid.uuid4()
    mock_trade = get_mock_trade(portfolio_id, primary_user["user_id"], trade_id)
    override_dependency.get_trade.return_value = mock_trade
    
    response = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}",
        headers=primary_user["headers"]
    )
    assert response.status_code == 200

    override_dependency.get_trade.side_effect = TradeNotFoundError()
    response = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}",
        headers=primary_user["headers"]
    )
    assert response.status_code == 404

async def test_create_trade(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    portfolio_id = uuid.uuid4()
    mock_trade = get_mock_trade(portfolio_id, primary_user["user_id"], uuid.uuid4())
    override_dependency.create_trade.return_value = mock_trade
    
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades",
        json={
            "symbol": "AAPL",
            "direction": "LONG",
            "asset_class": "EQUITY",
            "quantity": 1,
            "opened_at": datetime.now(timezone.utc).isoformat(),
            "entry_price": 100.0,
            "currency": "USD",
        },
        headers=primary_user["headers"]
    )
    assert response.status_code == 201

async def test_update_trade(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    portfolio_id = uuid.uuid4()
    trade_id = uuid.uuid4()
    mock_trade = get_mock_trade(portfolio_id, primary_user["user_id"], trade_id)
    override_dependency.update_trade.return_value = mock_trade
    
    response = await client.patch(
        f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}",
        json={"journal": "updated notes"},
        headers=primary_user["headers"]
    )
    assert response.status_code == 200

    override_dependency.update_trade.side_effect = TradeNotFoundError()
    response = await client.patch(
        f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}",
        json={"journal": "updated notes"},
        headers=primary_user["headers"]
    )
    assert response.status_code == 404

async def test_delete_trade(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    portfolio_id = uuid.uuid4()
    trade_id = uuid.uuid4()
    
    override_dependency.delete_trade.return_value = None
    response = await client.delete(
        f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}",
        headers=primary_user["headers"]
    )
    assert response.status_code == 204

    override_dependency.delete_trade.side_effect = TradeNotFoundError()
    response = await client.delete(
        f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}",
        headers=primary_user["headers"]
    )
    assert response.status_code == 404

async def test_partial_close_trade(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    portfolio_id = uuid.uuid4()
    trade_id = uuid.uuid4()
    
    mock_trade = get_mock_trade(portfolio_id, primary_user["user_id"], trade_id)
    override_dependency.partial_close_trade.return_value = mock_trade
    
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}/partial-close",
        json={"quantity": 5, "exit_price": 105.0, "closed_at": datetime.now(timezone.utc).isoformat()},
        headers=primary_user["headers"]
    )
    assert response.status_code == 200

    override_dependency.partial_close_trade.side_effect = TradeNotFoundError()
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}/partial-close",
        json={"quantity": 5, "exit_price": 105.0, "closed_at": datetime.now(timezone.utc).isoformat()},
        headers=primary_user["headers"]
    )
    assert response.status_code == 404

async def test_merge_trades(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    portfolio_id = uuid.uuid4()
    
    mock_trade = get_mock_trade(portfolio_id, primary_user["user_id"], uuid.uuid4())
    override_dependency.merge_trades.return_value = mock_trade
    
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades/merge",
        json={"trade_ids": [str(uuid.uuid4()), str(uuid.uuid4())]},
        headers=primary_user["headers"]
    )
    assert response.status_code == 200

    override_dependency.merge_trades.side_effect = ValueError("Bad merge")
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades/merge",
        json={"trade_ids": [str(uuid.uuid4()), str(uuid.uuid4())]},
        headers=primary_user["headers"]
    )
    assert response.status_code == 400

