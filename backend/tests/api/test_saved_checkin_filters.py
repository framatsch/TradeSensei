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

from app.api.v1.saved_checkin_filters import _get_service
from app.core.exceptions import (
    SavedCheckinFilterConflictError,
    SavedCheckinFilterNotFoundError,
)
from app.models.saved_checkin_filter import SavedCheckinFilter

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_service():
    mock = AsyncMock()
    # Mock return values
    from datetime import UTC, datetime
    filter_obj = SavedCheckinFilter(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name="Test Filter",
        filter_config={"field": "value"},
        is_default=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock.list_by_user.return_value = [filter_obj]
    mock.create.return_value = filter_obj
    mock.update.return_value = filter_obj
    mock.delete.return_value = None
    return mock


@pytest.fixture
def override_dependency(mock_service):
    from app.main import app
    app.dependency_overrides[_get_service] = lambda: mock_service
    yield mock_service
    app.dependency_overrides.clear()


async def test_list_saved_checkin_filters(
    client: AsyncClient,
    primary_user: dict[str, Any],
    override_dependency,
):
    response = await client.get(
        "/api/v1/checkins/filters",
        headers=primary_user["headers"],
    )
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1


async def test_create_saved_checkin_filter(
    client: AsyncClient,
    primary_user: dict[str, Any],
    override_dependency,
):
    response = await client.post(
        "/api/v1/checkins/filters",
        headers=primary_user["headers"],
        json={"name": "New Filter", "filter_config": {}},
    )
    assert response.status_code == 201

    override_dependency.create.side_effect = SavedCheckinFilterConflictError("Conflict")
    response = await client.post(
        "/api/v1/checkins/filters",
        headers=primary_user["headers"],
        json={"name": "New Filter", "filter_config": {}},
    )
    assert response.status_code == 409


async def test_update_saved_checkin_filter_success(
    client: AsyncClient,
    primary_user: dict[str, Any],
    override_dependency,
):
    f_id = uuid.uuid4()
    response = await client.put(
        f"/api/v1/checkins/filters/{f_id}",
        headers=primary_user["headers"],
        json={"name": "Updated Filter"},
    )
    assert response.status_code == 200


async def test_update_saved_checkin_filter_errors(
    client: AsyncClient,
    primary_user: dict[str, Any],
    override_dependency,
):
    f_id = uuid.uuid4()
    
    override_dependency.update.side_effect = SavedCheckinFilterNotFoundError("Not found")
    response = await client.put(f"/api/v1/checkins/filters/{f_id}", headers=primary_user["headers"], json={})
    assert response.status_code == 404
    
    override_dependency.update.side_effect = SavedCheckinFilterConflictError("Conflict")
    response = await client.put(f"/api/v1/checkins/filters/{f_id}", headers=primary_user["headers"], json={})
    assert response.status_code == 409


async def test_delete_saved_checkin_filter_success(
    client: AsyncClient,
    primary_user: dict[str, Any],
    override_dependency,
):
    f_id = uuid.uuid4()
    response = await client.delete(
        f"/api/v1/checkins/filters/{f_id}",
        headers=primary_user["headers"],
    )
    assert response.status_code == 204


async def test_delete_saved_checkin_filter_errors(
    client: AsyncClient,
    primary_user: dict[str, Any],
    override_dependency,
):
    f_id = uuid.uuid4()
    
    override_dependency.delete.side_effect = SavedCheckinFilterNotFoundError("Not found")
    response = await client.delete(f"/api/v1/checkins/filters/{f_id}", headers=primary_user["headers"])
    assert response.status_code == 404
