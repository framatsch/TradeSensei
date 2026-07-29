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

from app.api.v1.playbook_links import _get_service
from app.core.exceptions import (
    PlaybookLinkNotFoundError,
    PlaybookNotFoundError,
)
from app.schemas.playbook_link import PlaybookLinkResponse

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_service():
    mock = AsyncMock()
    # Mock return values
    from datetime import UTC, datetime
    link_res = PlaybookLinkResponse(
        id=uuid.uuid4(),
        playbook_id=uuid.uuid4(),
        url="https://example.com",
        label="Example",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock.list.return_value = [link_res]
    mock.create.return_value = link_res
    mock.delete.return_value = None
    return mock


@pytest.fixture
def override_dependency(mock_service):
    from app.main import app
    app.dependency_overrides[_get_service] = lambda: mock_service
    yield mock_service
    app.dependency_overrides.clear()


async def test_list_links(
    client: AsyncClient,
    primary_user: dict[str, Any],
    override_dependency,
):
    pb_id = uuid.uuid4()
    response = await client.get(
        f"/api/v1/playbooks/{pb_id}/links",
        headers=primary_user["headers"],
    )
    assert response.status_code == 200

    # Errors
    override_dependency.list.side_effect = PlaybookNotFoundError("Not found")
    response = await client.get(
        f"/api/v1/playbooks/{pb_id}/links",
        headers=primary_user["headers"],
    )
    assert response.status_code == 404


async def test_create_link(
    client: AsyncClient,
    primary_user: dict[str, Any],
    override_dependency,
):
    pb_id = uuid.uuid4()
    payload = {
        "url": "https://example.com",
        "label": "Example Link",
    }
    response = await client.post(
        f"/api/v1/playbooks/{pb_id}/links",
        headers=primary_user["headers"],
        json=payload,
    )
    assert response.status_code == 201

    # Errors
    override_dependency.create.side_effect = PlaybookNotFoundError("Not found")
    response = await client.post(
        f"/api/v1/playbooks/{pb_id}/links",
        headers=primary_user["headers"],
        json=payload,
    )
    assert response.status_code == 404


async def test_delete_link(
    client: AsyncClient,
    primary_user: dict[str, Any],
    override_dependency,
):
    pb_id = uuid.uuid4()
    link_id = uuid.uuid4()
    response = await client.delete(
        f"/api/v1/playbooks/{pb_id}/links/{link_id}",
        headers=primary_user["headers"],
    )
    assert response.status_code == 204

    # Errors
    override_dependency.delete.side_effect = PlaybookNotFoundError("Not found")
    response = await client.delete(
        f"/api/v1/playbooks/{pb_id}/links/{link_id}",
        headers=primary_user["headers"],
    )
    assert response.status_code == 404

    override_dependency.delete.side_effect = PlaybookLinkNotFoundError("Not found")
    response = await client.delete(
        f"/api/v1/playbooks/{pb_id}/links/{link_id}",
        headers=primary_user["headers"],
    )
    assert response.status_code == 404
