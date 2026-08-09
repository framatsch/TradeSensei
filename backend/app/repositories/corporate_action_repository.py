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

"""Async repository for the ``corporate_actions`` table.

All methods receive an :class:`AsyncSession` from the service layer and
return SQLAlchemy ORM instances.  No business logic lives here.
"""

import uuid
from datetime import date
from inspect import isawaitable

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.corporate_action import CorporateAction
from app.schemas.corporate_action import CorporateActionCreate, CorporateActionUpdate


class CorporateActionRepository:
    """Data-access object for the ``corporate_actions`` table.

    Every query is scoped to a ``user_id`` so that users can never see
    or modify each other's corporate actions.

    Args:
        session: An open :class:`AsyncSession` managed by the caller.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the repository with an existing session.

        Args:
            session: The database session to use for all queries.
        """
        self._session = session

    async def get_by_id(
        self,
        action_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> CorporateAction | None:
        """Retrieve a single corporate action by primary key, scoped to a user.

        Args:
            action_id: UUID of the corporate action to fetch.
            user_id: UUID of the requesting user — enforces ownership isolation.

        Returns:
            The matching :class:`CorporateAction`, or ``None`` if not found or
            not owned by the given user.
        """
        result = await self._session.execute(
            select(CorporateAction).where(
                CorporateAction.id == action_id,
                CorporateAction.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: uuid.UUID,
    ) -> list[CorporateAction]:
        """Return all corporate actions owned by the given user, ordered by date.

        Args:
            user_id: UUID of the requesting user.

        Returns:
            A list of :class:`CorporateAction` instances ordered ascending by
            ``date``, then ``symbol``.
        """
        result = await self._session.execute(
            select(CorporateAction).where(CorporateAction.user_id == user_id).order_by(CorporateAction.date.asc(), CorporateAction.symbol.asc())
        )
        return list(result.scalars().all())

    async def list_by_user_and_symbol(
        self,
        user_id: uuid.UUID,
        symbol: str,
    ) -> list[CorporateAction]:
        """Return corporate actions for a specific symbol, ordered by date.

        Args:
            user_id: UUID of the requesting user.
            symbol: Ticker symbol to filter by (case-sensitive exact match).

        Returns:
            A list of :class:`CorporateAction` instances for the given symbol,
            ordered ascending by ``date``.
        """
        result = await self._session.execute(
            select(CorporateAction)
            .where(
                CorporateAction.user_id == user_id,
                CorporateAction.symbol == symbol,
            )
            .order_by(CorporateAction.date.asc())
        )
        return list(result.scalars().all())

    async def list_by_user_and_symbol_or_conid(
        self,
        user_id: uuid.UUID,
        symbol: str,
        conid: str | None,
    ) -> list[CorporateAction]:
        """Return corporate actions filtered to a symbol and optional conid lineage.

        Args:
            user_id: UUID of the requesting user.
            symbol: Ticker symbol to filter by (case-sensitive exact match).
            conid: Optional contract identifier to match against ``old_conid``/
                ``new_conid`` lineage.

        Returns:
            A list of matching :class:`CorporateAction` instances ordered by date.
        """
        where_clause = [
            CorporateAction.user_id == user_id,
            CorporateAction.symbol == symbol,
        ]
        if conid is not None:
            where_clause.append(
                or_(
                    CorporateAction.old_conid == conid,
                    CorporateAction.new_conid == conid,
                    CorporateAction.old_conid.is_(None),
                    CorporateAction.new_conid.is_(None),
                )
            )

        result = await self._session.execute(select(CorporateAction).where(*where_clause).order_by(CorporateAction.date.asc()))
        scalars = result.scalars()
        if isawaitable(scalars):
            scalars = await scalars
        rows = scalars.all()
        if isawaitable(rows):
            rows = await rows
        return list(rows)

    async def list_by_user_in_date_range(
        self,
        user_id: uuid.UUID,
        from_date: date,
        to_date: date,
    ) -> list[CorporateAction]:
        """Return corporate actions for a user within an inclusive date range.

        Args:
            user_id: UUID of the requesting user.
            from_date: Start of the date range (inclusive).
            to_date: End of the date range (inclusive).

        Returns:
            A list of :class:`CorporateAction` instances within the range,
            ordered ascending by ``date``.
        """
        result = await self._session.execute(
            select(CorporateAction)
            .where(
                CorporateAction.user_id == user_id,
                CorporateAction.date >= from_date,
                CorporateAction.date <= to_date,
            )
            .order_by(CorporateAction.date.asc())
        )
        return list(result.scalars().all())

    async def create(self, data: CorporateActionCreate) -> CorporateAction:
        """Insert a new corporate action record.

        Args:
            data: Validated :class:`CorporateActionCreate` DTO, including
                the injected ``user_id``.

        Returns:
            The newly created and DB-refreshed :class:`CorporateAction` instance.
        """
        action = CorporateAction(
            user_id=data.user_id,
            symbol=data.symbol,
            date=data.date,
            ratio=data.ratio,
            old_conid=data.old_conid,
            new_conid=data.new_conid,
        )
        self._session.add(action)
        await self._session.flush()
        await self._session.refresh(action)
        return action

    async def find_by_user_symbol_date(
        self,
        user_id: uuid.UUID,
        symbol: str,
        action_date: date,
    ) -> CorporateAction | None:
        """Find a corporate action by uniqueness key.

        Args:
            user_id: Owning user UUID.
            symbol: Ticker symbol.
            action_date: Effective date.

        Returns:
            Matching corporate action or ``None``.
        """
        result = await self._session.execute(
            select(CorporateAction).where(
                CorporateAction.user_id == user_id,
                CorporateAction.symbol == symbol,
                CorporateAction.date == action_date,
            )
        )
        return result.scalar_one_or_none()

    async def update(
        self,
        action: CorporateAction,
        data: CorporateActionUpdate,
    ) -> CorporateAction:
        """Apply a partial update to an existing corporate action.

        Only fields present in ``data.model_fields_set`` are written.

        Args:
            action: The ORM instance to update.
            data: Validated :class:`CorporateActionUpdate` DTO.

        Returns:
            The updated :class:`CorporateAction` instance.
        """
        updates = data.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(action, field, value)
        await self._session.flush()
        await self._session.refresh(action)
        return action

    async def delete(self, action: CorporateAction) -> None:
        """Delete a corporate action record.

        Args:
            action: The ORM instance to delete.
        """
        await self._session.delete(action)
        await self._session.flush()
