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

"""Pydantic DTOs for broker sync request and response shapes."""

from datetime import datetime

from pydantic import BaseModel, Field


class BrokerStatusResponse(BaseModel):
    """Response schema describing the current broker connection status.

    Attributes:
        connected: ``True`` if an active connection exists for the
            authenticated user and the requested broker.
        last_sync_at: UTC timestamp of the most recent successful trade sync,
            or ``None`` if no sync has been performed.
    """

    connected: bool = Field(
        ...,
        description=("True if an active connection exists for this broker. False if the user has not connected or has disconnected."),
        examples=[True, False],
    )
    last_sync_at: datetime | None = Field(
        ...,
        description=("UTC timestamp of the most recent successful trade sync. Null if no sync has been performed since connecting."),
        examples=["2024-03-15T09:30:00Z", None],
    )


class BrokerSyncResult(BaseModel):
    """Response schema summarising the result of a broker account sync.

    Attributes:
        imported_count: Number of new trades successfully imported from
            the broker API during this sync operation.
        skipped_count: Number of orders that were skipped — either because
            they already exist (deduplicated by ``broker_order_id``) or
            because they could not be normalised.
        errors: List of human-readable error messages for orders that failed
            processing.  Empty when no errors occurred.
    """

    imported_count: int = Field(
        ...,
        ge=0,
        description="Number of new trades imported during this sync.",
        examples=[5, 0],
    )
    skipped_count: int = Field(
        ...,
        ge=0,
        description=("Number of orders skipped (already imported or could not be normalised)."),
        examples=[2, 0],
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Error messages for any orders that could not be processed.",
        examples=[[], ["Order 12345: unsupported asset type"]],
    )
