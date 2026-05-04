"""Object storage service for presigned upload URLs."""

import uuid
from datetime import UTC, datetime
from pathlib import Path

import boto3  # type: ignore
from fastapi import HTTPException, status

from app.core.config import settings


class StorageService:
    """Generate presigned URLs for direct object uploads."""

    _ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp"}

    def generate_screenshot_upload_url(
        self,
        user_id: uuid.UUID,
        filename: str,
        content_type: str,
    ) -> tuple[str, str]:
        """Create a presigned PUT URL and corresponding public URL."""
        if content_type not in self._ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="unsupported content_type",
            )

        if not settings.storage_backend:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="object storage is not configured",
            )

        if not settings.storage_bucket or not settings.storage_public_url:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="object storage is not configured",
            )

        clean_name = Path(filename).name
        if not clean_name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="filename is required",
            )

        key = (
            f"daily-checkins/{user_id}/"
            f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4()}-{clean_name}"
        )

        client = boto3.client(
            "s3",
            endpoint_url=settings.storage_endpoint_url,
            aws_access_key_id=settings.storage_access_key,
            aws_secret_access_key=settings.storage_secret_key,
        )
        presigned_url = client.generate_presigned_url(
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

    def generate_trade_image_upload_url(
        self,
        user_id: uuid.UUID,
        filename: str,
        content_type: str,
    ) -> tuple[str, str]:
        """Create a presigned PUT URL and corresponding public URL for a trade image."""
        if content_type not in self._ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="unsupported content_type",
            )

        if not settings.storage_backend:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="object storage is not configured",
            )

        if not settings.storage_bucket or not settings.storage_public_url:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="object storage is not configured",
            )

        clean_name = Path(filename).name
        if not clean_name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="filename is required",
            )

        key = (
            f"trades/{user_id}/"
            f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4()}-{clean_name}"
        )

        client = boto3.client(
            "s3",
            endpoint_url=settings.storage_endpoint_url,
            aws_access_key_id=settings.storage_access_key,
            aws_secret_access_key=settings.storage_secret_key,
        )
        presigned_url = client.generate_presigned_url(
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
