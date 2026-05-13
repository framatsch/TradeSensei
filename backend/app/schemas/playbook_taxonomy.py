"""Pydantic schemas for playbook taxonomy assignments."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PlaybookTaxonomyCreate(BaseModel):
    """Payload for assigning a taxonomy to a playbook."""

    taxonomy_id: uuid.UUID = Field(..., description="Taxonomy definition UUID to assign.")


class PlaybookTaxonomyResponse(BaseModel):
    """Response schema for a playbook taxonomy assignment."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Assignment identifier.")
    playbook_id: uuid.UUID = Field(..., description="Playbook identifier.")
    taxonomy_id: uuid.UUID = Field(..., description="Taxonomy identifier.")
    created_at: datetime = Field(..., description="UTC creation timestamp.")
