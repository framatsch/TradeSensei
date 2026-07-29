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
from datetime import UTC, date, datetime
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.api.v1.checkins import _get_service
from app.core.deps import get_session_with_rls
from app.core.exceptions import ConfigurationError, DailyCheckinNotFoundError, UnsupportedContentTypeError
from app.schemas.daily_checkin import DailyCheckinRead

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_service():
    mock = AsyncMock()
    return mock

@pytest.fixture
def override_dependency(mock_service):
    from app.main import app
    app.dependency_overrides[_get_service] = lambda: mock_service
    app.dependency_overrides[get_session_with_rls] = lambda: AsyncMock()
    yield mock_service
    app.dependency_overrides.clear()

def get_mock_checkin():
    return DailyCheckinRead(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        date=date(2024, 1, 1),
        rating=5,
        notes="Good day",
        market_phase="bullish",
        news_links=[],
        screenshot_urls=[],
        custom_metrics={},
        custom_fields={},
        is_manually_edited=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )

async def test_generate_screenshot_upload_url(client: AsyncClient, primary_user: dict[str, Any]):
    with patch("app.api.v1.checkins.StorageService") as mock_storage:
        mock_instance = mock_storage.return_value
        mock_instance.generate_screenshot_upload_url.return_value = ("http://presigned", "mykey")
        
        response = await client.post(
            "/api/v1/checkins/screenshot-upload-url",
            json={"filename": "test.png", "content_type": "image/png", "date": "2024-01-01"},
            headers=primary_user["headers"]
        )
        assert response.status_code == 200

        mock_instance.generate_screenshot_upload_url.side_effect = UnsupportedContentTypeError("Bad type")
        response = await client.post(
            "/api/v1/checkins/screenshot-upload-url",
            json={"filename": "test.txt", "content_type": "text/plain", "date": "2024-01-01"},
            headers=primary_user["headers"]
        )
        assert response.status_code == 422

        mock_instance.generate_screenshot_upload_url.side_effect = ConfigurationError("No storage")
        response = await client.post(
            "/api/v1/checkins/screenshot-upload-url",
            json={"filename": "test.png", "content_type": "image/png", "date": "2024-01-01"},
            headers=primary_user["headers"]
        )
        assert response.status_code == 503

async def test_create_checkin(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    override_dependency.create_checkin.return_value = get_mock_checkin()
    
    response = await client.post(
        "/api/v1/checkins",
        json={"date": "2024-01-01", "rating": 5, "notes": "Good day"},
        headers=primary_user["headers"]
    )
    assert response.status_code == 201

async def test_list_checkins(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    from app.schemas.daily_checkin import DailyCheckinListResponse
    override_dependency.list_checkins.return_value = DailyCheckinListResponse(items=[get_mock_checkin()], next_cursor=None, total=1)
    
    response = await client.get(
        "/api/v1/checkins?year=2024&month=1",
        headers=primary_user["headers"]
    )
    assert response.status_code == 200

async def test_get_checkin(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    override_dependency.get_checkin.return_value = get_mock_checkin()
    
    response = await client.get(
        "/api/v1/checkins/2024-01-01",
        headers=primary_user["headers"]
    )
    assert response.status_code == 200

    override_dependency.get_checkin.side_effect = DailyCheckinNotFoundError()
    response = await client.get(
        "/api/v1/checkins/2024-01-01",
        headers=primary_user["headers"]
    )
    assert response.status_code == 404

async def test_update_checkin(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    override_dependency.update_checkin.return_value = get_mock_checkin()
    
    response = await client.patch(
        "/api/v1/checkins/2024-01-01",
        json={"notes": "Updated"},
        headers=primary_user["headers"]
    )
    assert response.status_code == 200

    override_dependency.update_checkin.side_effect = DailyCheckinNotFoundError()
    response = await client.patch(
        "/api/v1/checkins/2024-01-01",
        json={"notes": "Updated"},
        headers=primary_user["headers"]
    )
    assert response.status_code == 404

async def test_delete_checkin(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    override_dependency.delete_checkin.return_value = None
    
    response = await client.delete(
        "/api/v1/checkins/2024-01-01",
        headers=primary_user["headers"]
    )
    assert response.status_code == 204

    override_dependency.delete_checkin.side_effect = DailyCheckinNotFoundError()
    response = await client.delete(
        "/api/v1/checkins/2024-01-01",
        headers=primary_user["headers"]
    )
    assert response.status_code == 404


async def test_list_checkins_invalid_uuid(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    response = await client.get(
        "/api/v1/checkins?taxonomy_ids=not-a-uuid",
        headers=primary_user["headers"]
    )
    assert response.status_code == 422

async def test_list_checkins_invalid_json(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    response = await client.get(
        "/api/v1/checkins?annotation_filters=not-json",
        headers=primary_user["headers"]
    )
    assert response.status_code == 422

async def test_create_checkin_errors(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    from app.core.exceptions import DailyCheckinAlreadyExistsError, DailyCheckinValidationError
    
    override_dependency.create_checkin.side_effect = DailyCheckinAlreadyExistsError("exists")
    response = await client.post(
        "/api/v1/checkins",
        json={"date": "2024-01-01", "rating": 5, "notes": "Good day"},
        headers=primary_user["headers"]
    )
    assert response.status_code == 409

    override_dependency.create_checkin.side_effect = DailyCheckinValidationError("bad")
    response = await client.post(
        "/api/v1/checkins",
        json={"date": "2024-01-01", "rating": 5, "notes": "Good day"},
        headers=primary_user["headers"]
    )
    assert response.status_code == 422

async def test_update_checkin_errors(client: AsyncClient, primary_user: dict[str, Any], override_dependency):
    from app.core.exceptions import DailyCheckinValidationError
    override_dependency.update_checkin.side_effect = DailyCheckinValidationError("bad")
    response = await client.patch(
        "/api/v1/checkins/2024-01-01",
        json={"notes": "Updated"},
        headers=primary_user["headers"]
    )
    assert response.status_code == 422
