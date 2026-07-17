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

from app.api.v1.playbook_attachments import _get_service
from app.core.exceptions import (
    ConfigurationError,
    PlaybookAttachmentNotFoundError,
    PlaybookNotFoundError,
    UnsupportedContentTypeError,
)
from app.schemas.playbook_attachment import (
    PlaybookImageResponse,
    PlaybookImageUploadUrlResponse,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_service():
    mock = AsyncMock()
    # Mock return values
    upload_url_res = PlaybookImageUploadUrlResponse(
        upload_url="https://s3.example.com/upload",
        key="playbooks/123/img.png",
    )
    mock.generate_upload_url.return_value = upload_url_res

    from datetime import datetime, UTC
    image_res = PlaybookImageResponse(
        id=uuid.uuid4(),
        playbook_id=uuid.uuid4(),
        filename="img.png",
        content_type="image/png",
        storage_url="https://s3.example.com/img.png",
        created_at=datetime.now(UTC),
    )
    mock.register.return_value = image_res
    mock.list.return_value = [image_res]
    mock.delete.return_value = None
    return mock


@pytest.fixture
def override_dependency(mock_service):
    from app.main import app
    app.dependency_overrides[_get_service] = lambda: mock_service
    yield mock_service
    app.dependency_overrides.clear()


async def test_generate_upload_url(
    client: AsyncClient,
    primary_user: dict[str, Any],
    override_dependency,
):
    pb_id = uuid.uuid4()
    response = await client.post(
        f"/api/v1/playbooks/{pb_id}/attachments/upload-url",
        headers=primary_user["headers"],
        json={"filename": "test.png", "content_type": "image/png"},
    )
    assert response.status_code == 200

    # Errors
    override_dependency.generate_upload_url.side_effect = PlaybookNotFoundError("Not found")
    response = await client.post(
        f"/api/v1/playbooks/{pb_id}/attachments/upload-url",
        headers=primary_user["headers"],
        json={"filename": "test.png", "content_type": "image/png"},
    )
    assert response.status_code == 404

    override_dependency.generate_upload_url.side_effect = UnsupportedContentTypeError("Bad content type")
    response = await client.post(
        f"/api/v1/playbooks/{pb_id}/attachments/upload-url",
        headers=primary_user["headers"],
        json={"filename": "test.png", "content_type": "image/png"},
    )
    assert response.status_code == 422

    override_dependency.generate_upload_url.side_effect = ConfigurationError("S3 not configured")
    response = await client.post(
        f"/api/v1/playbooks/{pb_id}/attachments/upload-url",
        headers=primary_user["headers"],
        json={"filename": "test.png", "content_type": "image/png"},
    )
    assert response.status_code == 503


async def test_register_attachment(
    client: AsyncClient,
    primary_user: dict[str, Any],
    override_dependency,
):
    pb_id = uuid.uuid4()
    payload = {
        "storage_url": "playbooks/123/img.png",
        "filename": "img.png",
        "content_type": "image/png",
    }
    response = await client.post(
        f"/api/v1/playbooks/{pb_id}/attachments",
        headers=primary_user["headers"],
        json=payload,
    )
    assert response.status_code == 201

    # Errors
    override_dependency.register.side_effect = PlaybookNotFoundError("Not found")
    response = await client.post(
        f"/api/v1/playbooks/{pb_id}/attachments",
        headers=primary_user["headers"],
        json=payload,
    )
    assert response.status_code == 404

    override_dependency.register.side_effect = UnsupportedContentTypeError("Bad type")
    response = await client.post(
        f"/api/v1/playbooks/{pb_id}/attachments",
        headers=primary_user["headers"],
        json=payload,
    )
    assert response.status_code == 422


async def test_list_attachments(
    client: AsyncClient,
    primary_user: dict[str, Any],
    override_dependency,
):
    pb_id = uuid.uuid4()
    response = await client.get(
        f"/api/v1/playbooks/{pb_id}/attachments",
        headers=primary_user["headers"],
    )
    assert response.status_code == 200

    # Errors
    override_dependency.list.side_effect = PlaybookNotFoundError("Not found")
    response = await client.get(
        f"/api/v1/playbooks/{pb_id}/attachments",
        headers=primary_user["headers"],
    )
    assert response.status_code == 404


async def test_delete_attachment(
    client: AsyncClient,
    primary_user: dict[str, Any],
    override_dependency,
):
    pb_id = uuid.uuid4()
    att_id = uuid.uuid4()
    response = await client.delete(
        f"/api/v1/playbooks/{pb_id}/attachments/{att_id}",
        headers=primary_user["headers"],
    )
    assert response.status_code == 204

    # Errors
    override_dependency.delete.side_effect = PlaybookNotFoundError("Not found")
    response = await client.delete(
        f"/api/v1/playbooks/{pb_id}/attachments/{att_id}",
        headers=primary_user["headers"],
    )
    assert response.status_code == 404

    override_dependency.delete.side_effect = PlaybookAttachmentNotFoundError("Not found")
    response = await client.delete(
        f"/api/v1/playbooks/{pb_id}/attachments/{att_id}",
        headers=primary_user["headers"],
    )
    assert response.status_code == 404
