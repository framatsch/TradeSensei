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

from app.api.v1.playbooks import _get_service
from app.core.exceptions import PlaybookAlreadyExistsError, PlaybookNotFoundError
from app.schemas.playbook import PlaybookRead

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_service():
    return AsyncMock()


@pytest.fixture
def override_dependency(mock_service):
    from app.main import app
    app.dependency_overrides[_get_service] = lambda: mock_service
    yield mock_service
    app.dependency_overrides.clear()


def make_playbook_read() -> PlaybookRead:
    return PlaybookRead(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name="Test Playbook",
        description="A cool playbook",
        is_active=True,
        target_winrate=0.5,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


async def test_list_playbooks(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    pb = make_playbook_read()
    override_dependency.list_playbooks.return_value = [pb]
    resp = await client.get("/api/v1/playbooks", headers=primary_user["headers"])
    assert resp.status_code == 200


async def test_create_playbook_success(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    pb = make_playbook_read()
    override_dependency.create_playbook.return_value = pb
    resp = await client.post("/api/v1/playbooks", headers=primary_user["headers"], json={"name": "New PB", "is_active": True})
    assert resp.status_code == 201


async def test_create_playbook_conflict(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    override_dependency.create_playbook.side_effect = PlaybookAlreadyExistsError("conflict")
    resp = await client.post("/api/v1/playbooks", headers=primary_user["headers"], json={"name": "Conflict PB"})
    assert resp.status_code == 409


async def test_get_playbook_success(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    pb = make_playbook_read()
    override_dependency.get_playbook.return_value = pb
    resp = await client.get(f"/api/v1/playbooks/{pb.id}", headers=primary_user["headers"])
    assert resp.status_code == 200


async def test_get_playbook_not_found(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    override_dependency.get_playbook.side_effect = PlaybookNotFoundError("not found")
    resp = await client.get(f"/api/v1/playbooks/{uuid.uuid4()}", headers=primary_user["headers"])
    assert resp.status_code == 404


async def test_update_playbook_success(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    pb = make_playbook_read()
    override_dependency.update_playbook.return_value = pb
    resp = await client.patch(f"/api/v1/playbooks/{pb.id}", headers=primary_user["headers"], json={"name": "Updated PB"})
    assert resp.status_code == 200


async def test_update_playbook_not_found(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    override_dependency.update_playbook.side_effect = PlaybookNotFoundError("not found")
    resp = await client.patch(f"/api/v1/playbooks/{uuid.uuid4()}", headers=primary_user["headers"], json={"name": "Updated PB"})
    assert resp.status_code == 404


async def test_delete_playbook_success(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    override_dependency.delete_playbook.return_value = None
    resp = await client.delete(f"/api/v1/playbooks/{uuid.uuid4()}", headers=primary_user["headers"])
    assert resp.status_code == 204


async def test_delete_playbook_not_found(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    override_dependency.delete_playbook.side_effect = PlaybookNotFoundError("not found")
    resp = await client.delete(f"/api/v1/playbooks/{uuid.uuid4()}", headers=primary_user["headers"])
    assert resp.status_code == 404
