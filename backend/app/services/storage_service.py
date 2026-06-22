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

"""Object storage service for presigned upload URLs."""

import re
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

    @staticmethod
    def parse_storage_ref(storage_ref: str) -> tuple[str, str]:
        if "://" in storage_ref:
            raise ValueError("storage_ref must be in '{bucket}/{key}' format")
        bucket, sep, key = storage_ref.partition("/")
        if not sep or not bucket or not key:
            raise ValueError("storage_ref must be in '{bucket}/{key}' format")
        return bucket, key

    @cached_property
    def _s3_client(self) -> Any:
        # Cached per-instance only — StorageService is instantiated per request.
        # Use public URL for presigning if available, otherwise internal endpoint.
        # This ensures the browser can reach the generated URL.
        endpoint = settings.storage_public_url or settings.storage_endpoint_url
        return boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=settings.storage_access_key,
            aws_secret_access_key=settings.storage_secret_key,
            config=boto3.session.Config(s3={"addressing_style": "path"}),  # type: ignore[attr-defined]
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

        if not settings.storage_bucket:
            raise ConfigurationError("object storage is not configured")

        clean_name = Path(filename).name
        if not clean_name:
            raise ValueError("filename is required")
        # Replace spaces and other S3-unsafe characters with underscores.
        # Spaces in S3 keys cause presigned URL signature mismatches with some
        # S3-compatible backends (including SeaweedFS) because boto3 encodes
        # spaces as %20 in the signed URL but the backend may expect a
        # different encoding when validating the signature.
        clean_name = re.sub(r"[^\w.\-]", "_", clean_name)

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

        storage_ref = f"{settings.storage_bucket}/{key}"
        return presigned_url, storage_ref

    def generate_presigned_get_url(self, storage_ref: str, expires_in: int = 3600) -> str:
        if not settings.storage_backend:
            return storage_ref
        bucket, key = self.parse_storage_ref(storage_ref)
        return self._s3_client.generate_presigned_url(  # type: ignore[no-any-return]
            ClientMethod="get_object",
            Params={
                "Bucket": bucket,
                "Key": key,
            },
            ExpiresIn=expires_in,
        )

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
            config=boto3.session.Config(s3={"addressing_style": "path"}),  # type: ignore[attr-defined]
        )

    def upload_file_content(
        self,
        content: bytes,
        key: str,
        content_type: str,
    ) -> str:
        if not settings.storage_bucket:
            raise ConfigurationError("object storage is not configured")

        self._s3_client_internal.put_object(
            Bucket=settings.storage_bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
        )

        storage_ref = f"{settings.storage_bucket}/{key}"
        return storage_ref

    def delete_file_by_storage_ref(
        self,
        storage_ref: str,
    ) -> None:
        bucket, key = self.parse_storage_ref(storage_ref)
        self._s3_client_internal.delete_object(
            Bucket=bucket,
            Key=key,
        )
