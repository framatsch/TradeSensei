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

"""Pydantic schemas for daily check-ins and related definitions."""

import datetime as dt
import uuid
from typing import Any

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, ValidationInfo, model_validator

from app.schemas.annotation_definition import CheckinAnnotationResponse
from app.schemas.taxonomy import TaxonomyResponse


class DailyCheckinCreate(BaseModel):
    """Payload for creating a daily check-in."""

    date: dt.date = Field(..., description="Check-in date in ISO 8601 format.")
    market_phase: str | None = Field(
        default=None,
        max_length=50,
        description="Optional market phase name; validated at service layer.",
    )
    target_index_ids: list[uuid.UUID] = Field(
        default_factory=list,
        description=("List of Market Index Definition UUIDs associated with this checkin."),
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
        description="Optional list of screenshot storage references in '{bucket}/{key}' format.",
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
    target_index_ids: list[uuid.UUID] | None = Field(
        default=None,
        description=("List of Market Index Definition UUIDs associated with this checkin."),
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
        description="Updated list of screenshot storage references in '{bucket}/{key}' format.",
    )
    custom_metrics: dict[str, int | bool] | None = Field(
        default=None,
        description="Updated custom metrics payload.",
    )


class TargetIndexRead(BaseModel):
    """Embedded target market index in check-in responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Unique market index identifier.")
    symbol: str = Field(..., description="Ticker symbol.")
    name: str = Field(..., description="Display name.")
    tradingview_url: str | None = Field(..., description="TradingView URL.")


class DailyCheckinRead(BaseModel):
    """Response schema for a daily check-in."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Unique check-in identifier.")
    user_id: uuid.UUID = Field(..., description="Owner user identifier.")
    date: dt.date = Field(..., description="Check-in date.")
    market_phase: str | None = Field(..., description="Stored market phase name.")
    notes: str | None = Field(..., description="Daily notes.")
    news_links: list[str] = Field(..., description="Validated news links.")
    screenshot_urls: list[str] = Field(
        ...,
        description="Short-lived presigned GET URLs for screenshots (expires in 1 hour).",
    )
    screenshot_keys: list[str] = Field(
        default_factory=list,
        description="Raw storage references in '{bucket}/{key}' format; use these when writing back screenshot_urls on PATCH.",
    )
    custom_metrics: dict[str, int | bool] | None = Field(..., description="Stored custom metric values.")
    target_indices: list[TargetIndexRead] = Field(
        default_factory=list,
        description="Associated market indices for this check-in.",
    )
    taxonomies: list[TaxonomyResponse] = Field(
        default_factory=list,
        description="Taxonomy definitions assigned to this check-in.",
    )
    annotations: list[CheckinAnnotationResponse] = Field(
        default_factory=list,
        description="Resolved annotation values assigned to this check-in.",
    )
    created_at: dt.datetime = Field(..., description="UTC creation timestamp.")
    updated_at: dt.datetime = Field(..., description="UTC last update timestamp.")

    @model_validator(mode="before")
    @classmethod
    def _resolve_metadata(cls, data: Any) -> Any:
        """Map assignment relationships into response fields."""
        if not isinstance(data, dict):
            if "taxonomy_assignments" in data.__dict__ and "taxonomies" not in data.__dict__:
                taxonomies = [
                    assignment.taxonomy
                    for assignment in data.__dict__["taxonomy_assignments"]
                    if getattr(assignment, "taxonomy", None) is not None
                ]
                data.__dict__["taxonomies"] = taxonomies

            if "annotation_assignments" in data.__dict__ and "annotations" not in data.__dict__:
                resolved_annotations: list[dict[str, Any]] = []
                for assignment in data.__dict__["annotation_assignments"]:
                    definition = getattr(assignment, "annotation_definition", None)
                    if definition is None:
                        continue
                    resolved_value: Any = assignment.value_int
                    if resolved_value is None:
                        resolved_value = assignment.value_float
                    if resolved_value is None:
                        resolved_value = assignment.value_bool
                    if resolved_value is None:
                        resolved_value = assignment.value_string
                    resolved_annotations.append(
                        {
                            "annotation_definition_id": definition.id,
                            "name": definition.name,
                            "type": definition.type,
                            "scope": definition.scope,
                            "icon_identifier": definition.icon_identifier,
                            "value": resolved_value,
                        }
                    )
                data.__dict__["annotations"] = resolved_annotations
        return data

    @model_validator(mode="after")
    def _resolve_screenshot_urls(self, info: ValidationInfo) -> "DailyCheckinRead":
        context = info.context if isinstance(info.context, dict) else None
        storage_service = context.get("storage_service") if context else None
        if storage_service is None:
            return self

        if not self.screenshot_urls:
            return self
            
        self.screenshot_keys = list(self.screenshot_urls)
        
        from app.core.config import settings

        self.screenshot_urls = [
            storage_service.generate_presigned_get_url(
                storage_ref=storage_ref,
                expires_in=settings.storage_presigned_get_ttl_seconds,
            )
            for storage_ref in self.screenshot_urls
        ]
        return self


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
    key: str = Field(..., description="Storage reference in {bucket}/{key} format to store in screenshot_urls.")


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
