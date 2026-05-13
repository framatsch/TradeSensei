"""Pydantic schemas for playbook external links."""

import uuid
from datetime import datetime

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator


class PlaybookLinkCreate(BaseModel):
    """Payload for adding a labeled external link to a playbook."""

    label: str = Field(..., min_length=1, max_length=200, description="Human-readable display label for the link.")
    url: AnyHttpUrl = Field(..., description="External URL (http or https).")

    @field_validator("label")
    @classmethod
    def validate_label(cls, value: str) -> str:
        """Ensure label is not only whitespace."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("label must not be empty or whitespace")
        return stripped


class PlaybookLinkResponse(BaseModel):
    """Response schema for a playbook external link."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Link identifier.")
    playbook_id: uuid.UUID = Field(..., description="Owning playbook identifier.")
    label: str = Field(..., description="Display label.")
    url: str = Field(..., description="External URL.")
    created_at: datetime = Field(..., description="UTC creation timestamp.")
