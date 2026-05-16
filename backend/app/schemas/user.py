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

"""Pydantic DTOs for User request and response shapes."""

import uuid
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, EmailStr, Field

from app.core.constants import (
    PASSWORD_MIN_LENGTH,
    USERNAME_MAX_LENGTH,
    USERNAME_MIN_LENGTH,
)


class UserCreate(BaseModel):
    """Request schema for registering a new user.

    Attributes:
        username: Chosen display name (3–50 characters).
        email: Valid email address used for login.
        password: Plain-text password (min 8 characters, write-only).
    """

    username: str = Field(
        ...,
        min_length=USERNAME_MIN_LENGTH,
        max_length=USERNAME_MAX_LENGTH,
        description="Unique display name (3–50 characters).",
        examples=["alice", "trader_bob"],
    )
    email: EmailStr = Field(
        ...,
        description="Valid email address used for authentication.",
        examples=["alice@example.com"],
    )
    password: str = Field(
        ...,
        min_length=PASSWORD_MIN_LENGTH,
        description=("Plain-text password (minimum 8 characters). Never stored or returned."),
        examples=["S3cur3P@ss!"],
    )


class UserRead(BaseModel):
    """Response schema for a single user.

    The ``hashed_password`` field is intentionally omitted.

    Attributes:
        id: UUID primary key.
        username: Display name.
        email: Email address.
        is_active: Whether the user account is active.
        created_at: UTC timestamp of account creation.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        ...,
        description="Unique user identifier (UUID v4).",
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )
    username: str = Field(
        ...,
        description="Display name.",
        examples=["alice"],
    )
    email: str = Field(
        ...,
        description="Email address.",
        examples=["alice@example.com"],
    )
    is_active: bool = Field(
        ...,
        description="Whether this user account is currently active.",
        examples=[True],
    )
    created_at: AwareDatetime = Field(
        ...,
        description="UTC timestamp of account creation.",
        examples=["2024-03-15T09:30:00Z"],
    )


class UserUpdate(BaseModel):
    """Request schema for partially updating the current user's profile.

    All fields are optional — only supplied fields are written.

    Attributes:
        username: Updated display name.
        email: Updated email address.
    """

    username: str | None = Field(
        default=None,
        min_length=USERNAME_MIN_LENGTH,
        max_length=USERNAME_MAX_LENGTH,
        description="Updated display name. Omit to leave unchanged.",
        examples=["alice_v2", None],
    )
    email: EmailStr | None = Field(
        default=None,
        description="Updated email address. Omit to leave unchanged.",
        examples=["newalice@example.com", None],
    )


class UserSettingsRead(BaseModel):
    """Response schema for a user's UI preferences.

    Attributes:
        theme: UI theme preference — ``"system"``, ``"light"``, or ``"dark"``.
        default_date_range: Default date range applied when no URL params are
            present — ``"all"``, ``"ytd"``, or ``"last30"``.
    """

    theme: Literal["system", "light", "dark"] = Field(
        default="system",
        description="UI theme preference.",
        examples=["system", "light", "dark"],
    )
    default_date_range: Literal["all", "ytd", "last30"] = Field(
        default="all",
        description=("Default date range filter for the trades page and dashboard. Applied when no URL query parameters are present."),
        examples=["all", "ytd", "last30"],
    )
    features: dict[str, bool] = Field(
        default_factory=dict,
        description="Per-user feature flags (map of flag key to boolean).",
        examples=[{"rolling_winrate_chart": True}],
    )
    chart_candles_before: int = Field(default=20, ge=1)
    chart_candles_after: int = Field(default=10, ge=1)
    chart_show_post_exit: bool = Field(default=False)
    default_portfolio_id: uuid.UUID | None = Field(default=None)
    home_route: Literal["/dashboard", "/dashboard/trades", "/dashboard/library", "/dashboard/checkins"] = Field(default="/dashboard")


class UserSettingsUpdate(BaseModel):
    """Request schema for updating a user's UI preferences.

    All fields are optional — only supplied fields are written.

    Attributes:
        theme: Updated theme preference.
        default_date_range: Updated default date range.
    """

    theme: Literal["system", "light", "dark"] | None = Field(
        default=None,
        description="Updated theme preference. Omit to leave unchanged.",
        examples=["dark", None],
    )
    default_date_range: Literal["all", "ytd", "last30"] | None = Field(
        default=None,
        description="Updated default date range. Omit to leave unchanged.",
        examples=["ytd", None],
    )
    features: dict[str, bool] | None = Field(
        default=None,
        description=("Partial update for per-user feature flags."),
        examples=[{"rolling_winrate_chart": True}, None],
    )
    chart_candles_before: int | None = Field(default=None, ge=1)
    chart_candles_after: int | None = Field(default=None, ge=1)
    chart_show_post_exit: bool | None = Field(default=None)
    default_portfolio_id: uuid.UUID | None = Field(default=None)
    home_route: (
        Literal[
            "/dashboard",
            "/dashboard/trades",
            "/dashboard/library",
            "/dashboard/checkins",
        ]
        | None
    ) = Field(default=None)


class UserLogin(BaseModel):
    """Request schema for the JSON-body login endpoint.

    Callers may identify themselves with either ``username`` or ``email``.

    Attributes:
        username: Username or email used to identify the account.
        password: Plain-text password.
    """

    username: str = Field(
        ...,
        description="Username or email address of the account to authenticate.",
        examples=["alice", "alice@example.com"],
    )
    password: str = Field(
        ...,
        description="Plain-text password.",
        examples=["S3cur3P@ss!"],
    )
