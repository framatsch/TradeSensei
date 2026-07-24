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

from app.api.v1.executions import _get_service
from app.core.deps import get_session_with_rls
from app.core.exceptions import ExecutionNotFoundError, ExecutionValidationError

from app.schemas.execution import LogicalExecutionRead, SplitExecutionResponse, MergeExecutionsResponse
from app.models.trade import AssetClass, Direction

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

def get_mock_execution(portfolio_id, user_id, execution_id, trade_id):
    return LogicalExecutionRead(
        id=execution_id,
        trade_id=trade_id,
        portfolio_id=portfolio_id,
        user_id=uuid.UUID(user_id),
        symbol="AAPL",
        asset_class=AssetClass.EQUITY,
        direction=Direction.LONG,
        quantity=Decimal("1"),
        price=Decimal("100.0"),
        executed_at=datetime.now(timezone.utc),
        multiplier=Decimal("1"),
        origin="manual",
        user_modified=False,
        commission=Decimal("0"),
        journal=None,
        is_manual=True,
        currency="USD",
        execution_time_original=datetime.now(timezone.utc),
        deleted=False,
        raw_transactions=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

async def test_list_trade_executions(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    portfolio_id = uuid.uuid4()
    trade_id = uuid.uuid4()
    mock_exec = get_mock_execution(portfolio_id, primary_user["user_id"], uuid.uuid4(), trade_id)
    
    override_dependency.list_trade_executions.return_value = [mock_exec]
    
    response = await client.get(
        f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}/executions",
        headers=primary_user["headers"]
    )
    assert response.status_code == 200

async def test_create_manual_execution(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    portfolio_id = uuid.uuid4()
    trade_id = uuid.uuid4()
    mock_exec = get_mock_execution(portfolio_id, primary_user["user_id"], uuid.uuid4(), trade_id)
    
    override_dependency.create_manual_execution.return_value = mock_exec
    
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/trades/{trade_id}/executions",
        json={
            "direction": "LONG",
            "quantity": 1,
            "price": 100.0,
            "executed_at": datetime.now(timezone.utc).isoformat()
        },
        headers=primary_user["headers"]
    )
    assert response.status_code == 201

async def test_update_execution(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    portfolio_id = uuid.uuid4()
    execution_id = uuid.uuid4()
    mock_exec = get_mock_execution(portfolio_id, primary_user["user_id"], execution_id, uuid.uuid4())
    
    override_dependency.update_execution.return_value = mock_exec
    
    response = await client.patch(
        f"/api/v1/portfolios/{portfolio_id}/executions/{execution_id}",
        json={"journal": "updated notes"},
        headers=primary_user["headers"]
    )
    assert response.status_code == 200

    override_dependency.update_execution.side_effect = ExecutionNotFoundError()
    response = await client.patch(
        f"/api/v1/portfolios/{portfolio_id}/executions/{execution_id}",
        json={"journal": "updated notes"},
        headers=primary_user["headers"]
    )
    assert response.status_code == 404

async def test_delete_execution(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    portfolio_id = uuid.uuid4()
    execution_id = uuid.uuid4()
    
    override_dependency.delete_execution.return_value = None
    response = await client.delete(
        f"/api/v1/portfolios/{portfolio_id}/executions/{execution_id}",
        headers=primary_user["headers"]
    )
    assert response.status_code == 204

    override_dependency.delete_execution.side_effect = ExecutionNotFoundError()
    response = await client.delete(
        f"/api/v1/portfolios/{portfolio_id}/executions/{execution_id}",
        headers=primary_user["headers"]
    )
    assert response.status_code == 404

async def test_restore_execution(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    portfolio_id = uuid.uuid4()
    execution_id = uuid.uuid4()
    mock_exec = get_mock_execution(portfolio_id, primary_user["user_id"], execution_id, uuid.uuid4())
    
    override_dependency.restore_execution.return_value = mock_exec
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/executions/{execution_id}/restore",
        headers=primary_user["headers"]
    )
    assert response.status_code == 200

    override_dependency.restore_execution.side_effect = ExecutionNotFoundError()
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/executions/{execution_id}/restore",
        headers=primary_user["headers"]
    )
    assert response.status_code == 404

async def test_split_execution(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    portfolio_id = uuid.uuid4()
    execution_id = uuid.uuid4()
    
    mock_exec1 = get_mock_execution(portfolio_id, primary_user["user_id"], uuid.uuid4(), uuid.uuid4())
    mock_exec2 = get_mock_execution(portfolio_id, primary_user["user_id"], uuid.uuid4(), uuid.uuid4())
    mock_original = get_mock_execution(portfolio_id, primary_user["user_id"], execution_id, uuid.uuid4())
    
    mock_result = SplitExecutionResponse(
        execution_a=mock_exec1,
        execution_b=mock_exec2,
        original=mock_original
    )
    override_dependency.split_execution.return_value = mock_result
    
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/executions/{execution_id}/split",
        json={"quantity_a": 0.5, "quantity_b": 0.5},
        headers=primary_user["headers"]
    )
    assert response.status_code == 200

    override_dependency.split_execution.side_effect = ExecutionNotFoundError()
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/executions/{execution_id}/split",
        json={"quantity_a": 0.5, "quantity_b": 0.5},
        headers=primary_user["headers"]
    )
    assert response.status_code == 404

async def test_merge_executions(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    portfolio_id = uuid.uuid4()
    
    mock_exec = get_mock_execution(portfolio_id, primary_user["user_id"], uuid.uuid4(), uuid.uuid4())
    
    mock_result = MergeExecutionsResponse(
        merged=mock_exec,
        sources=[mock_exec]
    )
    override_dependency.merge_executions.return_value = mock_result
    
    ex1 = str(uuid.uuid4())
    ex2 = str(uuid.uuid4())
    
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/executions/merge",
        json={"execution_ids": [ex1, ex2], "primary_id": ex1},
        headers=primary_user["headers"]
    )
    assert response.status_code == 200

    override_dependency.merge_executions.side_effect = ExecutionValidationError("Bad")
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/executions/merge",
        json={"execution_ids": [ex1, ex2], "primary_id": ex1},
        headers=primary_user["headers"]
    )
    assert response.status_code == 400

async def test_reassign_execution(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    portfolio_id = uuid.uuid4()
    execution_id = uuid.uuid4()
    
    mock_exec = get_mock_execution(portfolio_id, primary_user["user_id"], execution_id, uuid.uuid4())
    override_dependency.reassign_execution.return_value = mock_exec
    
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/executions/{execution_id}/reassign",
        json={"target_trade_id": str(uuid.uuid4())},
        headers=primary_user["headers"]
    )
    assert response.status_code == 200

    override_dependency.reassign_execution.side_effect = ExecutionNotFoundError()
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/executions/{execution_id}/reassign",
        json={"target_trade_id": str(uuid.uuid4())},
        headers=primary_user["headers"]
    )
    assert response.status_code == 404

async def test_detach_execution(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    portfolio_id = uuid.uuid4()
    execution_id = uuid.uuid4()
    
    from app.schemas.trade import TradeRead
    from app.models.trade import AssetClass, Direction
    from decimal import Decimal
    
    def get_mock_trade():
        return TradeRead(
            id=uuid.uuid4(),
            account_id=None,
            portfolio_id=portfolio_id,
            user_id=uuid.UUID(primary_user["user_id"]),
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
        
    override_dependency.detach_execution.return_value = get_mock_trade()
    
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/executions/{execution_id}/detach",
        headers=primary_user["headers"]
    )
    assert response.status_code == 200

    override_dependency.detach_execution.side_effect = ExecutionNotFoundError()
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/executions/{execution_id}/detach",
        headers=primary_user["headers"]
    )
    assert response.status_code == 404
