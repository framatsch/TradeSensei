"""Object storage service for presigned upload URLs."""

import uuid
from datetime import UTC, datetime
from functools import cached_property
from pathlib import Path
from typing import Any

import boto3

from app.core.config import settings
from app.core.exceptions import ConfigurationError, UnsupportedContentTypeError


class StorageService:
    """Generate presigned URLs for direct object uploads."""

    _ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp"}

    @cached_property
    def _s3_client(self) -> Any:
        # Cached per-instance only — StorageService is instantiated per request.
        return boto3.client(
            "s3",
            endpoint_url=settings.storage_endpoint_url,
            aws_access_key_id=settings.storage_access_key,
            aws_secret_access_key=settings.storage_secret_key,
        )

    def _generate_upload_url(
        self,
        *,
        key_prefix: str,
        user_id: uuid.UUID,
        filename: str,
        content_type: str,
    ) -> tuple[str, str]:
        if content_type not in self._ALLOWED_CONTENT_TYPES:
            raise UnsupportedContentTypeError("unsupported content_type")

        if not settings.storage_backend:
            raise ConfigurationError("object storage is not configured")

        if not settings.storage_bucket or not settings.storage_public_url:
            raise ConfigurationError("object storage is not configured")

        clean_name = Path(filename).name
        if not clean_name:
            raise ValueError("filename is required")

        key = f"{key_prefix}{user_id}/{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4()}-{clean_name}"

        presigned_url = self._s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": settings.storage_bucket,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=900,
        )

        public_url = f"{settings.storage_public_url.rstrip('/')}/{key}"
        return presigned_url, public_url

    def generate_screenshot_upload_url(
        self,
        user_id: uuid.UUID,
        filename: str,
        content_type: str,
    ) -> tuple[str, str]:
        """Create a presigned PUT URL and corresponding public URL."""
        return self._generate_upload_url(
            key_prefix="daily-checkins/",
            user_id=user_id,
            filename=filename,
            content_type=content_type,
        )

    def generate_trade_image_upload_url(
        self,
        user_id: uuid.UUID,
        filename: str,
        content_type: str,
    ) -> tuple[str, str]:
        """Create a presigned PUT URL and corresponding public URL for a trade image."""
        return self._generate_upload_url(
            key_prefix="trades/",
            user_id=user_id,
            filename=filename,
            content_type=content_type,
        )

    def generate_playbook_upload_url(
        self,
        user_id: uuid.UUID,
        filename: str,
        content_type: str,
    ) -> tuple[str, str]:
        """Create a presigned PUT URL and corresponding public URL for a playbook image."""
        return self._generate_upload_url(
            key_prefix="playbooks/",
            user_id=user_id,
            filename=filename,
            content_type=content_type,
        )

    @property
    def _s3_client_internal(self) -> Any:
        # Used for backend-initiated operations (put_object, delete_object).
        # Replaces localhost with seaweedfs if running in docker-compose defaults.
        import os

        endpoint = settings.storage_endpoint_url
        is_localhost = endpoint == "http://localhost:8333"
        is_docker = os.environ.get("KUBERNETES_SERVICE_HOST") is None
        is_test = os.environ.get("PYTEST_CURRENT_TEST") is not None
        if is_localhost and is_docker and not is_test:
            # We are likely running in local docker-compose with the default
            # localhost setting. Internal backend needs to route to the
            # seaweedfs container instead.
            endpoint = "http://seaweedfs:8333"

        return boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=settings.storage_access_key,
            aws_secret_access_key=settings.storage_secret_key,
        )

    def upload_file_content(
        self,
        content: bytes,
        key: str,
        content_type: str,
    ) -> str:
        """Upload raw bytes to object storage and return the public URL."""
        if not settings.storage_bucket or not settings.storage_public_url:
            raise ConfigurationError("object storage is not configured")

        self._s3_client_internal.put_object(
            Bucket=settings.storage_bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
        )

        public_url = f"{settings.storage_public_url.rstrip('/')}/{key}"
        return public_url

    def delete_file_by_url(
        self,
        public_url: str,
    ) -> None:
        """Extract the key from the public URL and delete the object."""
        if not settings.storage_bucket or not settings.storage_public_url:
            raise ConfigurationError("object storage is not configured")

        base = settings.storage_public_url.rstrip("/") + "/"
        if not public_url.startswith(base):
            return  # Not an object storage URL

        key = public_url[len(base) :]
        self._s3_client_internal.delete_object(
            Bucket=settings.storage_bucket,
            Key=key,
        )
