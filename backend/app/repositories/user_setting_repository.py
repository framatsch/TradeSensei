"""Async repository for the ``user_settings`` table.

All methods receive an :class:`AsyncSession` from the service layer and
return ORM instances or ``None``.  No business logic lives here.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_setting import UserSetting


class UserSettingRepository:
    """Data-access layer for the ``user_settings`` table.

    Attributes:
        _session: The async SQLAlchemy session used for all queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the repository with an active session.

        Args:
            session: An open :class:`~sqlalchemy.ext.asyncio.AsyncSession`.
        """
        self._session = session

    async def get_all_for_user(self, user_id: uuid.UUID) -> list[UserSetting]:
        """Return all settings rows for the given user.

        Args:
            user_id: UUID of the owning user.

        Returns:
            List of :class:`~app.models.user_setting.UserSetting` instances.
        """
        stmt = select(UserSetting).where(UserSetting.user_id == user_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def upsert(
        self,
        user_id: uuid.UUID,
        key: str,
        value: str,
    ) -> UserSetting:
        """Insert or update a single setting key-value pair.

        Uses ``INSERT ... ON CONFLICT (user_id, key) DO UPDATE`` for
        idempotent upserts. The session is **not** committed here —
        the caller (service layer) is responsible for committing.

        Args:
            user_id: UUID of the owning user.
            key: Setting key identifier (e.g. ``"theme"``).
            value: Setting value (e.g. ``"dark"``).

        Returns:
            The created or updated
            :class:`~app.models.user_setting.UserSetting` ORM instance.
        """
        values: dict[str, object] = {
            "user_id": user_id,
            "key": key,
            "value": value,
        }
        stmt = (
            pg_insert(UserSetting)
            .values(**values)
            .on_conflict_do_update(
                constraint="uq_user_settings_user_key",
                set_={"value": value},
            )
            .returning(UserSetting)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()
