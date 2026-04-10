"""Async repository for the ``corporate_actions`` table.

All methods receive an :class:`AsyncSession` from the service layer and
return SQLAlchemy ORM instances.  No business logic lives here.
"""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
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
            select(CorporateAction)
            .where(CorporateAction.user_id == user_id)
            .order_by(CorporateAction.date.asc(), CorporateAction.symbol.asc())
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

    async def find_by_user_symbol_date_ratio(
        self,
        user_id: uuid.UUID,
        symbol: str,
        action_date: date,
        ratio: Decimal,
    ) -> CorporateAction | None:
        """Find a corporate action by uniqueness key.

        Args:
            user_id: Owning user UUID.
            symbol: Ticker symbol.
            action_date: Effective date.
            ratio: Split ratio.

        Returns:
            Matching corporate action or ``None``.
        """
        result = await self._session.execute(
            select(CorporateAction).where(
                CorporateAction.user_id == user_id,
                CorporateAction.symbol == symbol,
                CorporateAction.date == action_date,
                CorporateAction.ratio == ratio,
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
