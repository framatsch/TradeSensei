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

"""Pydantic schemas for personal access token APIs."""

import uuid

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class PatGenerateRequest(BaseModel):
    """Request payload for creating a new personal access token."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable token name shown in settings.",
        examples=["Claude Desktop", "Cursor Local"],
    )
    expires_at: AwareDatetime | None = Field(
        default=None,
        description="Optional UTC expiration timestamp for the token.",
        examples=["2026-08-01T00:00:00Z", None],
    )


class PatRead(BaseModel):
    """Response payload for listing personal access tokens."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Unique token identifier.")
    name: str = Field(..., description="User-defined token name.")
    created_at: AwareDatetime = Field(..., description="UTC token creation timestamp.")
    expires_at: AwareDatetime | None = Field(..., description="UTC token expiry timestamp, or null if no expiry.")
    is_revoked: bool = Field(..., description="Whether the token has been revoked.")
    last_used_at: AwareDatetime | None = Field(..., description="UTC timestamp of last successful use, if any.")


class PatGenerateResponse(PatRead):
    """Response payload returned once when a token is created."""

    token: str = Field(
        ...,
        description=("Plaintext token shown exactly once. It is never returned again after creation."),
    )
