"""Pydantic DTOs for TradeNote request and response shapes."""

import uuid
from datetime import datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.core.constants import EMOTION_MAX_LENGTH, NOTE_MAX_LENGTH


class TradeNoteCreate(BaseModel):
    """Request schema for adding a note to a trade.

    Attributes:
        content: The body of the note (up to 10 000 characters).
        emotion: Optional emotion label (e.g. ``"fearful"``, ``"confident"``).
    """

    content: str = Field(
        ...,
        min_length=1,
        max_length=NOTE_MAX_LENGTH,
        description=(
            "Body of the trade note. Maximum 5 000 characters. "
            "Used for post-trade reviews, observations, or emotional state."
        ),
        examples=["Entered too early — should have waited for confirmation.", ""],
    )
    emotion: str | None = Field(
        default=None,
        max_length=EMOTION_MAX_LENGTH,
        description=(
            "Optional emotion label describing the trader's mental state "
            "when the note was written (e.g. 'fearful', 'confident', 'greedy'). "
            "Maximum 50 characters."
        ),
        examples=["fearful", "confident", "greedy", None],
    )


class TradeNoteUpdate(BaseModel):
    """Request schema for updating an existing trade note.

    All fields are optional — only supplied fields will be written.

    Attributes:
        content: Updated note body.
        emotion: Updated emotion label.
    """

    content: str | None = Field(
        default=None,
        min_length=1,
        max_length=NOTE_MAX_LENGTH,
        description="Updated note body. Omit to leave unchanged.",
        examples=["Actually, the setup was valid — I was too cautious.", None],
    )
    emotion: str | None = Field(
        default=None,
        max_length=EMOTION_MAX_LENGTH,
        description=(
            "Updated emotion label. Omit to leave unchanged. "
            "Set to null to clear the existing emotion."
        ),
        examples=["calm", None],
    )


class TradeNoteRead(BaseModel):
    """Response schema for a single trade note.

    Attributes:
        id: UUID primary key.
        trade_id: UUID of the parent trade.
        user_id: UUID of the author.
        content: Note body.
        emotion: Emotion label (``None`` if not set).
        created_at: UTC timestamp of note creation.
        updated_at: UTC timestamp of the last update.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        ...,
        description="Unique note identifier (UUID v4).",
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )
    trade_id: uuid.UUID = Field(
        ...,
        description="UUID of the trade this note belongs to.",
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )
    user_id: uuid.UUID = Field(
        ...,
        description="UUID of the user who wrote this note.",
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )
    content: str = Field(
        ...,
        description="Body of the note.",
        examples=["Entered too early — should have waited for confirmation."],
    )
    emotion: str | None = Field(
        ...,
        description="Emotion label at the time of writing. Null if not set.",
        examples=["fearful", None],
    )
    created_at: AwareDatetime = Field(
        ...,
        description="UTC timestamp of when this note was created.",
        examples=["2024-03-15T09:30:00Z"],
    )
    updated_at: datetime = Field(
        ...,
        description="UTC timestamp of the most recent update to this note.",
        examples=["2024-03-15T10:00:00Z"],
    )
