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
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.api.v1.annotation_definitions import _get_service
from app.core.exceptions import (
    AnnotationDefinitionNotFoundError,
    AnnotationDefinitionValidationError,
)
from app.main import app
from app.schemas.annotation_definition import AnnotationDefinitionResponse

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_annotation_service():
    return AsyncMock()


@pytest.fixture
def override_annotation_deps(mock_annotation_service):
    app.dependency_overrides[_get_service] = lambda: mock_annotation_service
    yield mock_annotation_service
    app.dependency_overrides.clear()


async def test_create_annotation_definition(
    client: AsyncClient, primary_user: dict[str, Any], override_annotation_deps
):
    mock_service = override_annotation_deps
    
    mock_service.create.return_value = AnnotationDefinitionResponse(
        id=uuid.uuid4(),
        user_id=uuid.UUID(primary_user["user_id"]),
        name="My Annotation",
        value_type="STRING",
        type="string_enum",
        description="desc",
        scale_labels={}, 
        icon_identifier="icon",
        scope="GLOBAL",
        is_archived=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    
    res = await client.post(
        "/api/v1/annotation-definitions",
        headers=primary_user["headers"],
        json={"name": "My Annotation", "type": "string_enum", "scope": "trades"},
    )
    assert res.status_code == 201, res.text

    mock_service.create.side_effect = AnnotationDefinitionValidationError("invalid")
    res2 = await client.post(
        "/api/v1/annotation-definitions",
        headers=primary_user["headers"],
        json={"name": "My Annotation", "type": "string_enum", "scope": "trades"},
    )
    assert res2.status_code == 409


async def test_list_annotation_definitions(
    client: AsyncClient, primary_user: dict[str, Any], override_annotation_deps
):
    mock_service = override_annotation_deps
    
    mock_service.list.return_value = []
    
    res = await client.get("/api/v1/annotation-definitions", headers=primary_user["headers"])
    assert res.status_code == 200, res.text


async def test_get_annotation_definition(
    client: AsyncClient, primary_user: dict[str, Any], override_annotation_deps
):
    mock_service = override_annotation_deps
    
    mock_service.get.return_value = AnnotationDefinitionResponse(
        id=uuid.uuid4(),
        user_id=uuid.UUID(primary_user["user_id"]),
        name="My Annotation",
        value_type="STRING",
        type="string_enum",
        description="desc",
        scale_labels={}, 
        icon_identifier="icon",
        scope="GLOBAL",
        is_archived=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    
    definition_id = str(uuid.uuid4())
    res = await client.get(
        f"/api/v1/annotation-definitions/{definition_id}",
        headers=primary_user["headers"],
    )
    assert res.status_code == 200, res.text

    mock_service.get.side_effect = AnnotationDefinitionNotFoundError("not found")
    res2 = await client.get(
        f"/api/v1/annotation-definitions/{definition_id}",
        headers=primary_user["headers"],
    )
    assert res2.status_code == 404


async def test_update_annotation_definition(
    client: AsyncClient, primary_user: dict[str, Any], override_annotation_deps
):
    mock_service = override_annotation_deps
    
    mock_service.update.return_value = AnnotationDefinitionResponse(
        id=uuid.uuid4(),
        user_id=uuid.UUID(primary_user["user_id"]),
        name="New Name",
        value_type="STRING",
        type="string_enum",
        description="desc",
        scale_labels={}, 
        icon_identifier="icon",
        scope="GLOBAL",
        is_archived=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    
    definition_id = str(uuid.uuid4())
    res = await client.put(
        f"/api/v1/annotation-definitions/{definition_id}",
        headers=primary_user["headers"],
        json={"name": "New Name"},
    )
    assert res.status_code == 200, res.text

    mock_service.update.side_effect = AnnotationDefinitionNotFoundError("not found")
    res2 = await client.put(
        f"/api/v1/annotation-definitions/{definition_id}",
        headers=primary_user["headers"],
        json={"name": "New Name"},
    )
    assert res2.status_code == 404

    mock_service.update.side_effect = AnnotationDefinitionValidationError("invalid")
    res3 = await client.put(
        f"/api/v1/annotation-definitions/{definition_id}",
        headers=primary_user["headers"],
        json={"name": "New Name"},
    )
    assert res3.status_code == 422


async def test_delete_annotation_definition(
    client: AsyncClient, primary_user: dict[str, Any], override_annotation_deps
):
    mock_service = override_annotation_deps
    
    mock_service.delete.return_value = None
    
    definition_id = str(uuid.uuid4())
    res = await client.delete(
        f"/api/v1/annotation-definitions/{definition_id}",
        headers=primary_user["headers"],
    )
    assert res.status_code == 204, res.text

    mock_service.delete.return_value = AnnotationDefinitionResponse(
        id=uuid.uuid4(),
        user_id=uuid.UUID(primary_user["user_id"]),
        name="Archived Def",
        value_type="STRING",
        type="string_enum",
        description="desc",
        scale_labels={}, 
        icon_identifier="icon",
        scope="GLOBAL",
        is_archived=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    res2 = await client.delete(
        f"/api/v1/annotation-definitions/{definition_id}",
        headers=primary_user["headers"],
    )
    assert res2.status_code == 200

    mock_service.delete.side_effect = AnnotationDefinitionNotFoundError("not found")
    res3 = await client.delete(
        f"/api/v1/annotation-definitions/{definition_id}",
        headers=primary_user["headers"],
    )
    assert res3.status_code == 404


async def test_archive_annotation_definition(
    client: AsyncClient, primary_user: dict[str, Any], override_annotation_deps
):
    mock_service = override_annotation_deps
    
    mock_service.archive.return_value = AnnotationDefinitionResponse(
        id=uuid.uuid4(),
        user_id=uuid.UUID(primary_user["user_id"]),
        name="My Annotation",
        value_type="STRING",
        type="string_enum",
        description="desc",
        scale_labels={}, 
        icon_identifier="icon",
        scope="GLOBAL",
        is_archived=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    
    definition_id = str(uuid.uuid4())
    res = await client.patch(
        f"/api/v1/annotation-definitions/{definition_id}/archive",
        headers=primary_user["headers"],
    )
    assert res.status_code == 200, res.text

    mock_service.archive.side_effect = AnnotationDefinitionNotFoundError("not found")
    res2 = await client.patch(
        f"/api/v1/annotation-definitions/{definition_id}/archive",
        headers=primary_user["headers"],
    )
    assert res2.status_code == 404


async def test_unarchive_annotation_definition(
    client: AsyncClient, primary_user: dict[str, Any], override_annotation_deps
):
    mock_service = override_annotation_deps
    
    mock_service.unarchive.return_value = AnnotationDefinitionResponse(
        id=uuid.uuid4(),
        user_id=uuid.UUID(primary_user["user_id"]),
        name="My Annotation",
        value_type="STRING",
        type="string_enum",
        description="desc",
        scale_labels={}, 
        icon_identifier="icon",
        scope="GLOBAL",
        is_archived=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    
    definition_id = str(uuid.uuid4())
    res = await client.patch(
        f"/api/v1/annotation-definitions/{definition_id}/unarchive",
        headers=primary_user["headers"],
    )
    assert res.status_code == 200, res.text

    mock_service.unarchive.side_effect = AnnotationDefinitionNotFoundError("not found")
    res2 = await client.patch(
        f"/api/v1/annotation-definitions/{definition_id}/unarchive",
        headers=primary_user["headers"],
    )
    assert res2.status_code == 404


async def test_get_annotation_definition_assignments_count(
    client: AsyncClient, primary_user: dict[str, Any], override_annotation_deps
):
    mock_service = override_annotation_deps
    
    mock_service.get_assignment_counts.return_value = {"trades": 5}
    
    definition_id = str(uuid.uuid4())
    res = await client.get(
        f"/api/v1/annotation-definitions/{definition_id}/assignments/count",
        headers=primary_user["headers"],
    )
    assert res.status_code == 200, res.text

    mock_service.get_assignment_counts.side_effect = AnnotationDefinitionNotFoundError("not found")
    res2 = await client.get(
        f"/api/v1/annotation-definitions/{definition_id}/assignments/count",
        headers=primary_user["headers"],
    )
    assert res2.status_code == 404
