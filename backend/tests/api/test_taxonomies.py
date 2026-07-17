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
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.api.v1.taxonomies import _get_service
from app.core.exceptions import TaxonomyNotFoundError, TaxonomyValidationError
from app.main import app
from app.schemas.taxonomy import TaxonomyResponse

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_taxonomy_service():
    return AsyncMock()


@pytest.fixture
def override_taxonomy_deps(mock_taxonomy_service):
    app.dependency_overrides[_get_service] = lambda: mock_taxonomy_service
    yield mock_taxonomy_service
    app.dependency_overrides.clear()


async def test_create_taxonomy(
    client: AsyncClient, primary_user: dict[str, Any], override_taxonomy_deps
):
    mock_service = override_taxonomy_deps
    
    mock_service.create.return_value = TaxonomyResponse(
        id=uuid.uuid4(),
        user_id=uuid.UUID(primary_user["user_id"]),
        name="My Taxonomy",
        scope="trades",
        color_hex="#FFFFFF",
        description="desc",
        icon_identifier="icon",
        is_archived=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    
    res = await client.post(
        "/api/v1/taxonomies",
        headers=primary_user["headers"],
        json={"name": "My Taxonomy", "scope": "trades", "color_hex": "#FFFFFF"},
    )
    assert res.status_code == 201, res.text

    mock_service.create.side_effect = TaxonomyValidationError("invalid")
    res2 = await client.post(
        "/api/v1/taxonomies",
        headers=primary_user["headers"],
        json={"name": "My Taxonomy", "scope": "trades", "color_hex": "#FFFFFF"},
    )
    assert res2.status_code == 409


async def test_list_taxonomies(
    client: AsyncClient, primary_user: dict[str, Any], override_taxonomy_deps
):
    mock_service = override_taxonomy_deps
    
    mock_service.list.return_value = []
    
    res = await client.get("/api/v1/taxonomies", headers=primary_user["headers"])
    assert res.status_code == 200, res.text


async def test_get_taxonomy(
    client: AsyncClient, primary_user: dict[str, Any], override_taxonomy_deps
):
    mock_service = override_taxonomy_deps
    
    mock_service.get.return_value = TaxonomyResponse(
        id=uuid.uuid4(),
        user_id=uuid.UUID(primary_user["user_id"]),
        name="My Taxonomy",
        scope="trades",
        color_hex="#FFFFFF",
        description="desc",
        icon_identifier="icon",
        is_archived=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    
    taxonomy_id = str(uuid.uuid4())
    res = await client.get(
        f"/api/v1/taxonomies/{taxonomy_id}",
        headers=primary_user["headers"],
    )
    assert res.status_code == 200, res.text

    mock_service.get.side_effect = TaxonomyNotFoundError("not found")
    res2 = await client.get(
        f"/api/v1/taxonomies/{taxonomy_id}",
        headers=primary_user["headers"],
    )
    assert res2.status_code == 404


async def test_update_taxonomy(
    client: AsyncClient, primary_user: dict[str, Any], override_taxonomy_deps
):
    mock_service = override_taxonomy_deps
    
    mock_service.update.return_value = TaxonomyResponse(
        id=uuid.uuid4(),
        user_id=uuid.UUID(primary_user["user_id"]),
        name="New Name",
        scope="trades",
        color_hex="#FFFFFF",
        description="desc",
        icon_identifier="icon",
        is_archived=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    
    taxonomy_id = str(uuid.uuid4())
    res = await client.patch(
        f"/api/v1/taxonomies/{taxonomy_id}",
        headers=primary_user["headers"],
        json={"name": "New Name"},
    )
    assert res.status_code == 200, res.text

    mock_service.update.side_effect = TaxonomyNotFoundError("not found")
    res2 = await client.patch(
        f"/api/v1/taxonomies/{taxonomy_id}",
        headers=primary_user["headers"],
        json={"name": "New Name"},
    )
    assert res2.status_code == 404

    mock_service.update.side_effect = TaxonomyValidationError("invalid")
    res3 = await client.patch(
        f"/api/v1/taxonomies/{taxonomy_id}",
        headers=primary_user["headers"],
        json={"name": "New Name"},
    )
    assert res3.status_code == 422


async def test_delete_taxonomy(
    client: AsyncClient, primary_user: dict[str, Any], override_taxonomy_deps
):
    mock_service = override_taxonomy_deps
    
    mock_service.delete.return_value = None
    
    taxonomy_id = str(uuid.uuid4())
    res = await client.delete(
        f"/api/v1/taxonomies/{taxonomy_id}",
        headers=primary_user["headers"],
    )
    assert res.status_code == 204, res.text

    mock_service.delete.return_value = TaxonomyResponse(
        id=uuid.uuid4(),
        user_id=uuid.UUID(primary_user["user_id"]),
        name="Archived Tax",
        scope="trades",
        color_hex="#FFFFFF",
        description="desc",
        icon_identifier="icon",
        is_archived=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    res2 = await client.delete(
        f"/api/v1/taxonomies/{taxonomy_id}",
        headers=primary_user["headers"],
    )
    assert res2.status_code == 200

    mock_service.delete.side_effect = TaxonomyNotFoundError("not found")
    res3 = await client.delete(
        f"/api/v1/taxonomies/{taxonomy_id}",
        headers=primary_user["headers"],
    )
    assert res3.status_code == 404


async def test_archive_taxonomy(
    client: AsyncClient, primary_user: dict[str, Any], override_taxonomy_deps
):
    mock_service = override_taxonomy_deps
    
    mock_service.archive.return_value = TaxonomyResponse(
        id=uuid.uuid4(),
        user_id=uuid.UUID(primary_user["user_id"]),
        name="My Taxonomy",
        scope="trades",
        color_hex="#FFFFFF",
        description="desc",
        icon_identifier="icon",
        is_archived=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    
    taxonomy_id = str(uuid.uuid4())
    res = await client.patch(
        f"/api/v1/taxonomies/{taxonomy_id}/archive",
        headers=primary_user["headers"],
    )
    assert res.status_code == 200, res.text

    mock_service.archive.side_effect = TaxonomyNotFoundError("not found")
    res2 = await client.patch(
        f"/api/v1/taxonomies/{taxonomy_id}/archive",
        headers=primary_user["headers"],
    )
    assert res2.status_code == 404


async def test_unarchive_taxonomy(
    client: AsyncClient, primary_user: dict[str, Any], override_taxonomy_deps
):
    mock_service = override_taxonomy_deps
    
    mock_service.unarchive.return_value = TaxonomyResponse(
        id=uuid.uuid4(),
        user_id=uuid.UUID(primary_user["user_id"]),
        name="My Taxonomy",
        scope="trades",
        color_hex="#FFFFFF",
        description="desc",
        icon_identifier="icon",
        is_archived=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    
    taxonomy_id = str(uuid.uuid4())
    res = await client.patch(
        f"/api/v1/taxonomies/{taxonomy_id}/unarchive",
        headers=primary_user["headers"],
    )
    assert res.status_code == 200, res.text

    mock_service.unarchive.side_effect = TaxonomyNotFoundError("not found")
    res2 = await client.patch(
        f"/api/v1/taxonomies/{taxonomy_id}/unarchive",
        headers=primary_user["headers"],
    )
    assert res2.status_code == 404


async def test_get_taxonomy_assignments_count(
    client: AsyncClient, primary_user: dict[str, Any], override_taxonomy_deps
):
    mock_service = override_taxonomy_deps
    
    mock_service.get_assignment_counts.return_value = {"trades": 5}
    
    taxonomy_id = str(uuid.uuid4())
    res = await client.get(
        f"/api/v1/taxonomies/{taxonomy_id}/assignments/count",
        headers=primary_user["headers"],
    )
    assert res.status_code == 200, res.text

    mock_service.get_assignment_counts.side_effect = TaxonomyNotFoundError("not found")
    res2 = await client.get(
        f"/api/v1/taxonomies/{taxonomy_id}/assignments/count",
        headers=primary_user["headers"],
    )
    assert res2.status_code == 404
