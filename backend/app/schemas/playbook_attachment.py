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

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field


class PlaybookImageUploadRequest(BaseModel):
    """Request payload to generate a presigned upload URL for a playbook image."""

    filename: str = Field(..., min_length=1, description="Original filename of the image.")
    content_type: str = Field(..., description="MIME type of the image (image/png, image/jpeg, image/webp, image/gif).")


class PlaybookImageUploadUrlResponse(BaseModel):
    """Response with presigned upload URL and public read URL."""

    upload_url: str = Field(..., description="Presigned PUT URL for direct upload to S3.")
    public_url: str = Field(..., description="Stable public URL that will be the attachment's storage_url after registration.")


class PlaybookImageRegisterRequest(BaseModel):
    """Request payload to register an uploaded image as a playbook attachment."""

    filename: str = Field(..., min_length=1, description="Original filename of the image.")
    content_type: str = Field(..., description="MIME type of the image.")
    storage_url: AnyHttpUrl = Field(..., description="Public URL of the uploaded image (must match STORAGE_PUBLIC_URL prefix).")


class PlaybookImageResponse(BaseModel):
    """Response schema for a registered playbook image attachment."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Attachment identifier.")
    playbook_id: uuid.UUID = Field(..., description="Owning playbook identifier.")
    filename: str = Field(..., description="Original filename.")
    content_type: str = Field(..., description="MIME type.")
    storage_url: str = Field(..., description="Stable public URL of the image.")
    created_at: datetime = Field(..., description="UTC creation timestamp.")
