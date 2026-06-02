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

        presigned_url, storage_ref = service._generate_upload_url(
            key_prefix="trades/",
            user_id=uuid.uuid4(),
            filename="chart.png",
            content_type="image/png",
        )

    assert presigned_url == "https://signed.example.com/upload"
    assert storage_ref.startswith("test-bucket/trades/")
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


@pytest.mark.unit
def test_generate_presigned_get_url_default_expiry(configured_storage: None) -> None:
    service = StorageService()
    with patch("app.services.storage_service.boto3.client") as client_factory:
        client = Mock()
        client.generate_presigned_url.return_value = "https://signed.example.com/get"
        client_factory.return_value = client

        result = service.generate_presigned_get_url("test-bucket/trades/u1/file.png")

    assert result == "https://signed.example.com/get"
    kwargs = client.generate_presigned_url.call_args.kwargs
    assert kwargs["ClientMethod"] == "get_object"
    assert kwargs["Params"]["Bucket"] == "test-bucket"
    assert kwargs["Params"]["Key"] == "trades/u1/file.png"
    assert kwargs["ExpiresIn"] == 3600


@pytest.mark.unit
def test_generate_presigned_get_url_custom_expiry(configured_storage: None) -> None:
    service = StorageService()
    with patch("app.services.storage_service.boto3.client") as client_factory:
        client = Mock()
        client.generate_presigned_url.return_value = "https://signed.example.com/get"
        client_factory.return_value = client

        service.generate_presigned_get_url("other-bucket/playbooks/u1/file.png", expires_in=4 * 3600)

    kwargs = client.generate_presigned_url.call_args.kwargs
    assert kwargs["Params"]["Bucket"] == "other-bucket"
    assert kwargs["Params"]["Key"] == "playbooks/u1/file.png"
    assert kwargs["ExpiresIn"] == 4 * 3600


@pytest.mark.unit
def test_generate_upload_url_returns_storage_ref_bucket_prefix(configured_storage: None) -> None:
    service = StorageService()
    with patch("app.services.storage_service.boto3.client") as client_factory:
        client = Mock()
        client.generate_presigned_url.return_value = "https://signed.example.com/upload"
        client_factory.return_value = client

        _, storage_ref = service._generate_upload_url(
            key_prefix="daily-checkins/",
            user_id=uuid.uuid4(),
            filename="chart.png",
            content_type="image/png",
        )

    assert storage_ref.startswith("test-bucket/")
