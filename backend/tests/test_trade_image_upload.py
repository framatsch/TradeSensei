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

"""Tests for trade image upload endpoints and schema validation."""


import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.schemas.trade import TradeCreateRequest, TradeUpdate
from tests.test_trades_api import _get_auth_headers


@pytest.fixture
def override_storage_settings(monkeypatch: pytest.MonkeyPatch):
    """Fixture to mock storage settings."""
    monkeypatch.setattr(settings, "storage_backend", "s3")
    monkeypatch.setattr(settings, "storage_bucket", "test-bucket")
    monkeypatch.setattr(settings, "storage_proxy_url", "https://storage.test")
    monkeypatch.setattr(settings, "storage_endpoint_url", "https://s3.test")
    monkeypatch.setattr(settings, "storage_access_key", "test-key")
    monkeypatch.setattr(settings, "storage_secret_key", "test-secret")
    return settings


@pytest.mark.asyncio
async def test_generate_trade_image_upload_url_success(
    client: AsyncClient,
    override_storage_settings,
) -> None:
    """Test generating a presigned URL successfully."""
    headers = await _get_auth_headers(client, "test1")
    response = await client.post(
        "/api/v1/trades/upload-url",
        json={"filename": "chart.png", "content_type": "image/png"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert "presigned_url" in data
    assert "key" in data
    assert data["key"].startswith("test-bucket/trades/")
    assert "chart.png" in data["key"]


@pytest.mark.asyncio
async def test_generate_trade_image_upload_url_unauthorized(
    client: AsyncClient,
) -> None:
    """Test generating a presigned URL without auth fails."""
    response = await client.post(
        "/api/v1/trades/upload-url",
        json={"filename": "chart.png", "content_type": "image/png"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_generate_trade_image_upload_url_invalid_type(
    client: AsyncClient,
    override_storage_settings,
) -> None:
    """Test generating a presigned URL with invalid content type fails."""
    headers = await _get_auth_headers(client, "test2")
    response = await client.post(
        "/api/v1/trades/upload-url",
        json={"filename": "malicious.exe", "content_type": "application/x-msdownload"},
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_generate_trade_image_upload_url_storage_not_configured(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test generating a presigned URL when storage is disabled."""
    monkeypatch.setattr(settings, "storage_backend", None)
    headers = await _get_auth_headers(client, "test3")
    
    response = await client.post(
        "/api/v1/trades/upload-url",
        json={"filename": "chart.png", "content_type": "image/png"},
        headers=headers,
    )
    assert response.status_code == 503


def test_schema_validation_success(override_storage_settings):
    valid_ref = "test-bucket/trades/some-id/chart.png"

    req = TradeCreateRequest(
        symbol="AAPL",
        direction="LONG",
        asset_class="EQUITY",
        quantity="10",
        entry_price="150",
        opened_at="2024-01-01T10:00:00Z",
        image_urls=[valid_ref],
    )
    assert req.image_urls == [valid_ref]

    upd = TradeUpdate(image_urls=[valid_ref])
    assert upd.image_urls == [valid_ref]


def test_schema_validation_rejects_full_url(override_storage_settings):
    with pytest.raises(ValueError, match="image_urls entries must use"):
        TradeCreateRequest(
            symbol="AAPL",
            direction="LONG",
            asset_class="EQUITY",
            quantity="10",
            entry_price="150",
            opened_at="2024-01-01T10:00:00Z",
            image_urls=["https://malicious.test/image.png"],
        )

    with pytest.raises(ValueError, match="image_urls entries must use"):
        TradeUpdate(image_urls=["https://malicious.test/image.png"])


def test_schema_validation_rejects_wrong_bucket(override_storage_settings):
    with pytest.raises(ValueError, match="configured storage bucket"):
        TradeUpdate(image_urls=["other-bucket/trades/image.png"])


def test_schema_validation_allows_any_bucket_when_unconfigured(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "storage_bucket", None)
    upd = TradeUpdate(image_urls=["any-bucket/trades/image.png"])
    assert upd.image_urls == ["any-bucket/trades/image.png"]
