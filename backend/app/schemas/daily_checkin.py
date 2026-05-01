"""Pydantic schemas for daily check-ins and related definitions."""

import datetime as dt
import re
import uuid

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator

from app.models.daily_checkin import FieldTypeEnum

_KEBAB_CASE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


class CheckinFieldDefinitionCreate(BaseModel):
    """Payload for creating a check-in field definition."""

    field_name: str = Field(
        ...,
        max_length=100,
        description="Stable field key in lowercase kebab-case.",
    )
    field_type: FieldTypeEnum = Field(
        ...,
        description="Allowed field type: integer or boolean.",
    )

    @field_validator("field_name")
    @classmethod
    def validate_kebab_case(cls, value: str) -> str:
        """Validate that a key is lowercase kebab-case."""
        if not _KEBAB_CASE_RE.fullmatch(value):
            raise ValueError("field_name must be lowercase kebab-case")
        return value


class CheckinFieldDefinitionUpdate(BaseModel):
    """Payload for updating a check-in field definition."""

    model_config = ConfigDict(extra="forbid")

    field_name: str | None = Field(
        default=None,
        max_length=100,
        description="Updated lowercase kebab-case field key.",
    )
    is_active: bool | None = Field(
        default=None,
        description="Whether this field can be used in new check-ins.",
    )

    @field_validator("field_name")
    @classmethod
    def validate_kebab_case(cls, value: str | None) -> str | None:
        """Validate that a key is lowercase kebab-case when provided."""
        if value is None:
            return None
        if not _KEBAB_CASE_RE.fullmatch(value):
            raise ValueError("field_name must be lowercase kebab-case")
        return value


class CheckinFieldDefinitionRead(BaseModel):
    """Response schema for a check-in field definition."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Unique definition identifier.")
    user_id: uuid.UUID = Field(..., description="Owner user identifier.")
    field_name: str = Field(..., description="Stable field key.")
    field_type: FieldTypeEnum = Field(..., description="Field value type.")
    is_active: bool = Field(..., description="Whether the field is currently active.")
    created_at: dt.datetime = Field(
        ...,
        description="UTC timestamp when the field was created.",
    )


class MarketPhaseDefinitionCreate(BaseModel):
    """Payload for creating a market phase definition."""

    name: str = Field(
        ...,
        max_length=50,
        description="Stable phase key in lowercase kebab-case.",
    )
    label: str = Field(..., max_length=100, description="User-facing phase label.")
    color_hex: str = Field(
        default="#6366f1",
        description="Hex color in #RRGGBB format.",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Validate lowercase kebab-case phase name."""
        if not _KEBAB_CASE_RE.fullmatch(value):
            raise ValueError("name must be lowercase kebab-case")
        return value

    @field_validator("color_hex")
    @classmethod
    def validate_color_hex(cls, value: str) -> str:
        """Validate 6-digit hex color."""
        if not _HEX_COLOR_RE.fullmatch(value):
            raise ValueError("color_hex must be a 6-digit hex color")
        return value


class MarketPhaseDefinitionUpdate(BaseModel):
    """Payload for updating a market phase definition."""

    model_config = ConfigDict(extra="forbid")

    label: str | None = Field(
        default=None,
        max_length=100,
        description="Updated user-facing phase label.",
    )
    color_hex: str | None = Field(
        default=None,
        description="Updated hex color in #RRGGBB format.",
    )
    is_active: bool | None = Field(
        default=None,
        description="Whether this phase can be used in new check-ins.",
    )

    @field_validator("color_hex")
    @classmethod
    def validate_color_hex(cls, value: str | None) -> str | None:
        """Validate 6-digit hex color when provided."""
        if value is None:
            return None
        if not _HEX_COLOR_RE.fullmatch(value):
            raise ValueError("color_hex must be a 6-digit hex color")
        return value


class MarketPhaseDefinitionRead(BaseModel):
    """Response schema for a market phase definition."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Unique definition identifier.")
    user_id: uuid.UUID = Field(..., description="Owner user identifier.")
    name: str = Field(..., description="Stable storage key for the phase.")
    label: str = Field(..., description="Display label for the phase.")
    color_hex: str = Field(..., description="Hex color used for this phase.")
    is_active: bool = Field(..., description="Whether the phase is currently active.")
    created_at: dt.datetime = Field(
        ...,
        description="UTC timestamp when the phase was created.",
    )


class DailyCheckinCreate(BaseModel):
    """Payload for creating a daily check-in."""

    date: dt.date = Field(..., description="Check-in date in ISO 8601 format.")
    market_phase: str | None = Field(
        default=None,
        max_length=50,
        description="Optional market phase name; validated at service layer.",
    )
    notes: str | None = Field(
        default=None,
        max_length=10_000,
        description="Optional free-form note for the day.",
    )
    news_links: list[AnyHttpUrl] = Field(
        default_factory=list,
        max_length=10,
        description="Optional list of up to 10 news links.",
    )
    screenshot_urls: list[str] = Field(
        default_factory=list,
        description="Optional list of screenshot URLs.",
    )
    custom_metrics: dict[str, int | bool] | None = Field(
        default=None,
        description="Optional custom metrics keyed by field_name.",
    )


class DailyCheckinUpdate(BaseModel):
    """Payload for updating a daily check-in."""

    market_phase: str | None = Field(
        default=None,
        max_length=50,
        description="Updated market phase name; validated at service layer.",
    )
    notes: str | None = Field(
        default=None,
        max_length=10_000,
        description="Updated free-form note.",
    )
    news_links: list[AnyHttpUrl] | None = Field(
        default=None,
        max_length=10,
        description="Updated list of up to 10 news links.",
    )
    screenshot_urls: list[str] | None = Field(
        default=None,
        description="Updated list of screenshot URLs.",
    )
    custom_metrics: dict[str, int | bool] | None = Field(
        default=None,
        description="Updated custom metrics payload.",
    )


class DailyCheckinRead(BaseModel):
    """Response schema for a daily check-in."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Unique check-in identifier.")
    user_id: uuid.UUID = Field(..., description="Owner user identifier.")
    date: dt.date = Field(..., description="Check-in date.")
    market_phase: str | None = Field(..., description="Stored market phase name.")
    notes: str | None = Field(..., description="Daily notes.")
    news_links: list[str] = Field(..., description="Validated news links.")
    screenshot_urls: list[str] = Field(..., description="Stored screenshot URLs.")
    custom_metrics: dict[str, int | bool] | None = Field(
        ..., description="Stored custom metric values."
    )
    created_at: dt.datetime = Field(..., description="UTC creation timestamp.")
    updated_at: dt.datetime = Field(..., description="UTC last update timestamp.")


class ScreenshotUploadUrlRequest(BaseModel):
    """Request schema to obtain a screenshot upload URL."""

    filename: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Original file name.",
    )
    content_type: str = Field(
        ...,
        description="MIME type of the file to upload.",
    )


class ScreenshotUploadUrlResponse(BaseModel):
    """Response schema containing presigned and public URLs."""

    presigned_url: str = Field(..., description="Short-lived presigned PUT URL.")
    public_url: str = Field(..., description="Public URL to store in screenshot_urls.")


class DailyCheckinListResponse(BaseModel):
    """Cursor-paginated list response for daily check-ins."""

    items: list[DailyCheckinRead] = Field(
        ...,
        description="List of check-ins for the current page.",
    )
    next_cursor: dt.date | None = Field(
        ...,
        description="Date cursor for the next page; null on last page.",
    )
    total: int = Field(..., description="Total number of matching check-ins.")
    model_config = ConfigDict(extra="forbid")
