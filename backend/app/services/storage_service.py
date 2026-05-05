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

        key = (
            f"{key_prefix}{user_id}/"
            f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4()}-{clean_name}"
        )

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
