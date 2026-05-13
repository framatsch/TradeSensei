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
