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

import uuid
from datetime import datetime
from typing import Literal

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
    schwab_oauth_mode: str | None = Field(
        default=None,
        description="The configured Schwab OAuth mode ('paste' or 'callback').",
        examples=["paste", "callback", None],
    )


class SchwabAuthorizeResponse(BaseModel):
    """Response payload containing Schwab OAuth authorization URL."""

    authorization_url: str = Field(
        ...,
        description="Absolute Schwab OAuth authorization URL.",
        examples=["https://api.schwabapi.com/v1/oauth/authorize?response_type=code&..."],
    )


class SchwabCompleteRequest(BaseModel):
    """Request payload for pasted Schwab OAuth redirect URL completion."""

    redirect_url: str = Field(
        ...,
        min_length=1,
        description="Full redirect URL copied from the browser address bar after Schwab consent.",
        examples=["https://127.0.0.1/?code=abc&state=xyz"],
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
    warnings: list[str] = Field(
        default_factory=list,
        description="Informational or warning messages.",
    )
    trades_protected_reconciled: int = Field(
        default=0,
        description="Number of metadata-protected trades that absorbed new executions.",
    )
    trades_protected_skipped: int = Field(
        default=0,
        description="Number of metadata-protected positions skipped.",
    )
    activity_log: list[str] = Field(
        default_factory=list,
        description=("Informational log of routine, successful row-level outcomes ('created:'/'updated:'/'skipped:' lines). Not an error or warning signal."),
    )


class BrokerConnectionTestRequest(BaseModel):
    """Request payload to validate broker credentials for an account type.

    Attributes:
        type: Broker/account type to validate.
        properties: Optional plaintext credential map. When omitted on edit,
            stored encrypted account credentials are used.
        account_id: Optional existing account UUID for edit-mode validation.
    """

    type: Literal["schwab", "ibkr"] = Field(
        ...,
        description="Broker type to validate. Only 'schwab' and 'ibkr' support connection tests.",
        examples=["ibkr", "schwab"],
    )
    properties: dict[str, str] | None = Field(
        default=None,
        description=("Optional plaintext credential overrides keyed by provider field name (e.g. IBKR_FLEX_TOKEN)."),
    )
    account_id: uuid.UUID | None = Field(
        default=None,
        description="Optional account ID to use stored encrypted credentials for missing fields.",
    )


class BrokerConnectionTestResult(BaseModel):
    """Response payload for broker credential validation."""

    success: bool = Field(
        ...,
        description="True when the credential test call succeeded.",
        examples=[True, False],
    )
    message: str = Field(
        ...,
        description="Human-readable outcome summary.",
        examples=["Connection successful.", "Missing account property: IBKR_FLEX_TOKEN"],
    )
