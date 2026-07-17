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
from typing import Any
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.api.v1.saved_trade_filters import get_saved_trade_filter_service
from app.core.exceptions import (
    SavedTradeFilterNotFoundError,
    SavedTradeFilterPermissionError,
    SavedTradeFilterValidationError,
)
from app.models.saved_trade_filter import SavedTradeFilter
from app.schemas.saved_trade_filter import SavedTradeFilterCreate, SavedTradeFilterUpdate

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_service():
    mock = AsyncMock()
    # Mock return values
    from app.models.saved_trade_filter import FilterScope
    from datetime import datetime, UTC
    filter_obj = SavedTradeFilter(
        id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        name="Test Filter",
        definition={"field": "value"},
        scope=FilterScope.USER,
        needs_review=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock.list_for_user.return_value = [filter_obj]
    mock.create_user_filter.return_value = filter_obj
    mock.update_user_filter.return_value = filter_obj
    mock.delete_user_filter.return_value = None
    return mock


@pytest.fixture
def override_dependency(mock_service):
    from app.main import app
    app.dependency_overrides[get_saved_trade_filter_service] = lambda: mock_service
    yield mock_service
    app.dependency_overrides.clear()


async def test_list_saved_trade_filters(
    client: AsyncClient,
    primary_user: dict[str, Any],
    override_dependency,
):
    response = await client.get(
        "/api/v1/saved-trade-filters",
        headers=primary_user["headers"],
    )
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1


async def test_create_saved_trade_filter(
    client: AsyncClient,
    primary_user: dict[str, Any],
    override_dependency,
):
    response = await client.post(
        "/api/v1/saved-trade-filters",
        headers=primary_user["headers"],
        json={"name": "New Filter", "definition": {}},
    )
    assert response.status_code == 201


async def test_update_saved_trade_filter_success(
    client: AsyncClient,
    primary_user: dict[str, Any],
    override_dependency,
):
    f_id = uuid.uuid4()
    response = await client.patch(
        f"/api/v1/saved-trade-filters/{f_id}",
        headers=primary_user["headers"],
        json={"name": "Updated Filter"},
    )
    assert response.status_code == 200


async def test_update_saved_trade_filter_errors(
    client: AsyncClient,
    primary_user: dict[str, Any],
    override_dependency,
):
    f_id = uuid.uuid4()
    
    override_dependency.update_user_filter.side_effect = SavedTradeFilterNotFoundError("Not found")
    response = await client.patch(f"/api/v1/saved-trade-filters/{f_id}", headers=primary_user["headers"], json={})
    assert response.status_code == 404
    
    override_dependency.update_user_filter.side_effect = SavedTradeFilterPermissionError("Forbidden")
    response = await client.patch(f"/api/v1/saved-trade-filters/{f_id}", headers=primary_user["headers"], json={})
    assert response.status_code == 403

    override_dependency.update_user_filter.side_effect = SavedTradeFilterValidationError("Unprocessable")
    response = await client.patch(f"/api/v1/saved-trade-filters/{f_id}", headers=primary_user["headers"], json={})
    assert response.status_code == 422


async def test_delete_saved_trade_filter_success(
    client: AsyncClient,
    primary_user: dict[str, Any],
    override_dependency,
):
    f_id = uuid.uuid4()
    response = await client.delete(
        f"/api/v1/saved-trade-filters/{f_id}",
        headers=primary_user["headers"],
    )
    assert response.status_code == 204


async def test_delete_saved_trade_filter_errors(
    client: AsyncClient,
    primary_user: dict[str, Any],
    override_dependency,
):
    f_id = uuid.uuid4()
    
    override_dependency.delete_user_filter.side_effect = SavedTradeFilterNotFoundError("Not found")
    response = await client.delete(f"/api/v1/saved-trade-filters/{f_id}", headers=primary_user["headers"])
    assert response.status_code == 404
    
    override_dependency.delete_user_filter.side_effect = SavedTradeFilterPermissionError("Forbidden")
    response = await client.delete(f"/api/v1/saved-trade-filters/{f_id}", headers=primary_user["headers"])
    assert response.status_code == 403

