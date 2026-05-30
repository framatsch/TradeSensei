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

"""Business-logic service for user profile operations.

Provides read, update, and delete operations scoped to the currently
authenticated user.  All domain exceptions raised here are caught by
the route layer.
"""

import json
import logging
import uuid
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UserAlreadyExistsError, UserNotFoundError
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.repositories.user_setting_repository import UserSettingRepository
from app.schemas.user import UserRead, UserSettingsRead, UserSettingsUpdate, UserUpdate

# Keys supported by the settings system with their defaults.
_SETTINGS_DEFAULTS: dict[str, object] = {
    "theme": "system",
    "default_date_range": "all",
    "features": "{}",
    "chart_candles_before": "20",
    "chart_candles_after": "10",
    "chart_show_post_exit": False,
    "default_portfolio_id": None,
    "show_open_trades": False,
    "home_route": "/dashboard",
}

logger = logging.getLogger(__name__)


class UserService:
    """Service layer for user profile management.

    All operations are implicitly scoped to the requesting user so that
    no user can read or modify another user's profile.

    Args:
        session: An open :class:`AsyncSession` managed by the caller.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with a database session.

        Args:
            session: The session to use for all operations.
        """
        self._session = session
        self._repo = UserRepository(session)
        self._settings_repo = UserSettingRepository(session)

    async def get_user(self, user_id: uuid.UUID) -> UserRead:
        """Return the profile DTO for the given user.

        Args:
            user_id: UUID of the user to retrieve.

        Returns:
            A :class:`~app.schemas.user.UserRead` DTO for the user.

        Raises:
            :class:`~app.core.exceptions.UserNotFoundError`: If the user
                no longer exists (should be rare in normal operation).
        """
        user = await self._repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(f"User {user_id} not found.")
        return UserRead.model_validate(user)

    async def update_user(self, user: User, data: UserUpdate) -> UserRead:
        """Apply a partial update to the given user's profile.

        Checks that any new username or email is not already taken by a
        different user before writing.

        Args:
            user: The ORM instance of the authenticated user.
            data: Validated partial update payload.

        Returns:
            A :class:`~app.schemas.user.UserRead` DTO reflecting the
            updated state.

        Raises:
            :class:`~app.core.exceptions.UserAlreadyExistsError`: If the
                requested username or email is already in use by another user.
        """
        update_dict = data.model_dump(exclude_unset=True)

        # Enforce uniqueness before writing
        new_username: str | None = update_dict.get("username")
        if new_username is not None and new_username != user.username:
            existing = await self._repo.get_by_username(new_username)
            if existing is not None:
                raise UserAlreadyExistsError(f"Username {new_username!r} is already taken.")

        new_email: str | None = update_dict.get("email")
        if new_email is not None and new_email != user.email:
            existing = await self._repo.get_by_email(new_email)
            if existing is not None:
                raise UserAlreadyExistsError(f"Email {new_email!r} is already registered.")

        # Strip None values — only write explicitly-provided non-null fields
        clean_dict: dict[str, object] = {k: v for k, v in update_dict.items() if v is not None}
        updated = await self._repo.update(user, clean_dict)
        return UserRead.model_validate(updated)

    async def delete_user(self, user: User) -> None:
        """Permanently delete the given user and all owned data.

        Args:
            user: The ORM instance of the authenticated user to delete.
        """
        await self._repo.delete(user)

    async def get_settings(self, user_id: uuid.UUID) -> UserSettingsRead:
        """Return the UI preferences for the given user.

        Missing keys are filled in with their default values so the response
        always contains a complete settings object.

        Args:
            user_id: UUID of the authenticated user.

        Returns:
            A :class:`~app.schemas.user.UserSettingsRead` with all keys
            populated (defaults applied for any missing rows).
        """
        rows = await self._settings_repo.get_all_for_user(user_id)
        stored: dict[str, str] = {row.key: row.value for row in rows}
        # Ensure features is present as JSON string if absent
        if "features" not in stored:
            stored["features"] = str(_SETTINGS_DEFAULTS["features"])
        # Merge defaults and stored settings
        merged: dict[str, str | dict[str, bool]] = {}
        for k, v in _SETTINGS_DEFAULTS.items():
            merged[k] = cast(str | dict[str, bool], v)
        for k, v in stored.items():
            merged[k] = cast(str | dict[str, bool], v)
        # Deserialize features JSON into dict
        try:
            features_val = merged.get("features", "{}")
            merged_features = json.loads(features_val) if isinstance(features_val, str) else features_val
        except Exception:
            logger.warning(
                "Failed to parse features JSON for user %s",
                user_id,
                exc_info=True,
            )
            merged_features = {}
        merged["features"] = merged_features

        if merged.get("home_route") not in {
            "/dashboard",
            "/dashboard/trades",
            "/dashboard/library",
            "/dashboard/checkins",
        }:
            merged["home_route"] = "/dashboard"

        if merged.get("default_portfolio_id") in ("None", "null"):
            merged["default_portfolio_id"] = None  # type: ignore[assignment]

        show_open_trades = merged.get("show_open_trades")
        if isinstance(show_open_trades, str):
            merged["show_open_trades"] = show_open_trades.lower() == "true"

        chart_show_post_exit = merged.get("chart_show_post_exit")
        if isinstance(chart_show_post_exit, str):
            merged["chart_show_post_exit"] = chart_show_post_exit.lower() == "true"

        return UserSettingsRead(**merged)  # type: ignore[arg-type]  # Type narrowing from dynamic settings dict is imperfect for mypy.

    async def update_settings(
        self,
        user_id: uuid.UUID,
        data: UserSettingsUpdate,
    ) -> UserSettingsRead:
        """Persist changed settings keys and return the full updated settings.

        Only keys present in ``data`` (non-None values) are written. Unchanged
        keys retain their current values (or defaults if never set).

        Args:
            user_id: UUID of the authenticated user.
            data: Partial settings update payload.

        Returns:
            A :class:`~app.schemas.user.UserSettingsRead` reflecting all
            current settings after the update.
        """
        update_dict = data.model_dump(exclude_unset=True)

        # Handle features merge specially
        features_update = update_dict.pop("features", None)
        if features_update is not None:
            # Read current features value
            rows = await self._settings_repo.get_all_for_user(user_id)
            stored: dict[str, str] = {row.key: row.value for row in rows}
            current_features = {}
            if "features" in stored:
                try:
                    current_features = json.loads(stored["features"])
                except Exception:
                    logger.warning(
                        "Failed to parse features JSON for user %s",
                        user_id,
                        exc_info=True,
                    )
                    current_features = {}
            # Merge (incoming keys overwrite)
            merged_features = {**current_features, **(features_update or {})}
            await self._settings_repo.upsert(
                user_id=user_id,
                key="features",
                value=json.dumps(merged_features),
            )

        for key, value in update_dict.items():
            if value is not None and key != "features":
                await self._settings_repo.upsert(
                    user_id=user_id,
                    key=key,
                    value=str(value),
                )
        await self._session.commit()
        # expire_all() is required here: upsert() uses
        # pg_insert().on_conflict_do_update() which bypasses the SQLAlchemy
        # ORM identity map. Without this, get_settings() returns stale values.
        self._session.expire_all()
        return await self.get_settings(user_id)
