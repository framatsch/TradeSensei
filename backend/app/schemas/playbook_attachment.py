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

"""Pydantic schemas for playbook image attachments."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, model_validator


class PlaybookImageUploadRequest(BaseModel):
    """Request payload to generate a presigned upload URL for a playbook image."""

    filename: str = Field(..., min_length=1, description="Original filename of the image.")
    content_type: str = Field(..., description="MIME type of the image (image/png, image/jpeg, image/webp, image/gif).")


class PlaybookImageUploadUrlResponse(BaseModel):
    """Response with presigned upload URL and public read URL."""

    upload_url: str = Field(..., description="Presigned PUT URL for direct upload to S3.")
    key: str = Field(..., description="Storage reference in {bucket}/{key} format to register as attachment storage_url.")


class PlaybookImageRegisterRequest(BaseModel):
    """Request payload to register an uploaded image as a playbook attachment."""

    filename: str = Field(..., min_length=1, description="Original filename of the image.")
    content_type: str = Field(..., description="MIME type of the image.")
    storage_url: str = Field(..., description="Uploaded image storage reference in {bucket}/{key} format.")


class PlaybookImageResponse(BaseModel):
    """Response schema for a registered playbook image attachment."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Attachment identifier.")
    playbook_id: uuid.UUID = Field(..., description="Owning playbook identifier.")
    filename: str = Field(..., description="Original filename.")
    content_type: str = Field(..., description="MIME type.")
    storage_url: str = Field(..., description="Short-lived presigned GET URL of the image.")
    created_at: datetime = Field(..., description="UTC creation timestamp.")

    @model_validator(mode="after")
    def _resolve_storage_url(self, info: ValidationInfo) -> "PlaybookImageResponse":
        context = info.context if isinstance(info.context, dict) else None
        storage_service = context.get("storage_service") if context else None
        if storage_service is None or not self.storage_url:
            return self
        from app.core.config import settings

        self.storage_url = storage_service.generate_presigned_get_url(
            storage_ref=self.storage_url,
            expires_in=settings.storage_presigned_get_ttl_playbook_seconds,
        )
        return self
