"""Unit tests for StorageService URL generation."""

import uuid
from unittest.mock import Mock, patch

import pytest

from app.core.config import settings
from app.core.exceptions import ConfigurationError, UnsupportedContentTypeError
from app.services.storage_service import StorageService


@pytest.fixture
def configured_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "storage_backend", "s3")
    monkeypatch.setattr(settings, "storage_bucket", "test-bucket")
    monkeypatch.setattr(settings, "storage_public_url", "https://storage.test")


@pytest.mark.unit
def test_generate_upload_url_happy_path_calls_presigned_url(
    configured_storage: None,
) -> None:
    service = StorageService()
    with patch("app.services.storage_service.boto3.client") as client_factory:
        client = Mock()
        client.generate_presigned_url.return_value = "https://signed.example.com/upload"
        client_factory.return_value = client

        presigned_url, public_url = service._generate_upload_url(
            key_prefix="trades/",
            user_id=uuid.uuid4(),
            filename="chart.png",
            content_type="image/png",
        )

    assert presigned_url == "https://signed.example.com/upload"
    assert public_url.startswith("https://storage.test/trades/")
    client.generate_presigned_url.assert_called_once()
    kwargs = client.generate_presigned_url.call_args.kwargs
    assert kwargs["ClientMethod"] == "put_object"
    assert kwargs["Params"]["Bucket"] == "test-bucket"
    assert kwargs["Params"]["ContentType"] == "image/png"


@pytest.mark.unit
def test_generate_upload_url_rejects_unsupported_content_type(
    configured_storage: None,
) -> None:
    service = StorageService()
    with pytest.raises(UnsupportedContentTypeError):
        service._generate_upload_url(
            key_prefix="trades/",
            user_id=uuid.uuid4(),
            filename="chart.pdf",
            content_type="application/pdf",
        )


@pytest.mark.unit
def test_generate_upload_url_raises_when_storage_backend_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "storage_backend", None)
    monkeypatch.setattr(settings, "storage_bucket", "test-bucket")
    monkeypatch.setattr(settings, "storage_public_url", "https://storage.test")
    service = StorageService()

    with pytest.raises(ConfigurationError):
        service._generate_upload_url(
            key_prefix="trades/",
            user_id=uuid.uuid4(),
            filename="chart.png",
            content_type="image/png",
        )


@pytest.mark.unit
def test_generate_upload_url_raises_for_empty_filename(configured_storage: None) -> None:
    service = StorageService()
    with pytest.raises(ValueError):
        service._generate_upload_url(
            key_prefix="trades/",
            user_id=uuid.uuid4(),
            filename="",
            content_type="image/png",
        )
