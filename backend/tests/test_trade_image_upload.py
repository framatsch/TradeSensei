"""Tests for trade image upload endpoints and schema validation."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.schemas.trade import TradeCreateRequest, TradeUpdate
from tests.test_trades_api import _get_auth_headers

@pytest.fixture
def override_storage_settings(monkeypatch: pytest.MonkeyPatch):
    """Fixture to mock storage settings."""
    monkeypatch.setattr(settings, "storage_backend", "s3")
    monkeypatch.setattr(settings, "storage_bucket", "test-bucket")
    monkeypatch.setattr(settings, "storage_public_url", "https://storage.test")
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
    assert "public_url" in data
    assert data["public_url"].startswith("https://storage.test/trades/")
    assert "chart.png" in data["public_url"]


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
    """Test TradeCreateRequest and TradeUpdate validation succeeds with valid URLs."""
    valid_url = "https://storage.test/trades/some-id-chart.png"
    
    req = TradeCreateRequest(
        symbol="AAPL",
        direction="LONG",
        asset_class="EQUITY",
        quantity="10",
        entry_price="150",
        opened_at="2024-01-01T10:00:00Z",
        image_urls=[valid_url],
    )
    assert req.image_urls == [valid_url]
    
    upd = TradeUpdate(image_urls=[valid_url])
    assert upd.image_urls == [valid_url]


def test_schema_validation_invalid_url(override_storage_settings):
    """Test validation fails if URL does not match STORAGE_PUBLIC_URL."""
    invalid_url = "https://malicious.test/image.png"
    
    with pytest.raises(ValueError, match="image URL must start with"):
        TradeCreateRequest(
            symbol="AAPL",
            direction="LONG",
            asset_class="EQUITY",
            quantity="10",
            entry_price="150",
            opened_at="2024-01-01T10:00:00Z",
            image_urls=[invalid_url],
        )

    with pytest.raises(ValueError, match="image URL must start with"):
        TradeUpdate(image_urls=[invalid_url])


def test_schema_validation_storage_not_configured(monkeypatch: pytest.MonkeyPatch):
    """Test validation fails if image_urls provided but storage is not configured."""
    monkeypatch.setattr(settings, "storage_public_url", None)
    
    with pytest.raises(ValueError, match="storage_public_url is not configured"):
        TradeUpdate(image_urls=["https://some.url/image.png"])
