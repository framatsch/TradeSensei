"""Async repository for the ``broker_connections`` table.

All methods receive an :class:`AsyncSession` from the service layer and
return SQLAlchemy ORM instances or ``None``.  No business logic lives here.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.broker_connection import BrokerConnection


class BrokerConnectionRepository:
    """Data-access layer for the ``broker_connections`` table.

    Attributes:
        _session: The async SQLAlchemy session used for all queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the repository with an active session.

        Args:
            session: An open :class:`~sqlalchemy.ext.asyncio.AsyncSession`.
        """
        self._session = session

    async def get_by_user_broker(
        self,
        user_id: uuid.UUID,
        broker: str,
    ) -> BrokerConnection | None:
        """Retrieve a broker connection for a specific user and broker.

        Args:
            user_id: UUID of the owning user.
            broker: Broker identifier (e.g. ``"schwab"``).

        Returns:
            The matching :class:`~app.models.broker_connection.BrokerConnection`
            ORM instance, or ``None`` if no connection exists.
        """
        stmt = select(BrokerConnection).where(
            BrokerConnection.user_id == user_id,
            BrokerConnection.broker == broker,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        user_id: uuid.UUID,
        broker: str,
        access_token: str,
        refresh_token: str,
        token_expires_at: datetime,
    ) -> BrokerConnection:
        """Insert or update a broker connection using a PostgreSQL upsert.

        Uses ``INSERT ... ON CONFLICT (user_id, broker) DO UPDATE`` to ensure
        idempotent token storage.  The session is **not** committed here —
        the caller (service layer) is responsible for committing.

        Args:
            user_id: UUID of the owning user.
            broker: Broker identifier (e.g. ``"schwab"``).
            access_token: Fernet-encrypted OAuth access token.
            refresh_token: Fernet-encrypted OAuth refresh token.
            token_expires_at: UTC timestamp when the access token expires.

        Returns:
            The created or updated
            :class:`~app.models.broker_connection.BrokerConnection` ORM
            instance, refreshed from the database.
        """
        values: dict[str, object] = {
            "user_id": user_id,
            "broker": broker,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_expires_at": token_expires_at,
        }
        stmt = (
            pg_insert(BrokerConnection)
            .values(**values)
            .on_conflict_do_update(
                constraint="uq_broker_connections_user_broker",
                set_={
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_expires_at": token_expires_at,
                },
            )
            .returning(BrokerConnection)
        )
        result = await self._session.execute(stmt)
        connection = result.scalar_one()
        return connection

    async def update_last_sync(
        self,
        user_id: uuid.UUID,
        broker: str,
    ) -> None:
        """Update the ``last_sync_at`` timestamp to the current time.

        Args:
            user_id: UUID of the owning user.
            broker: Broker identifier (e.g. ``"schwab"``).
        """
        from sqlalchemy import func

        stmt = (
            update(BrokerConnection)
            .where(
                BrokerConnection.user_id == user_id,
                BrokerConnection.broker == broker,
            )
            .values(last_sync_at=func.now())
        )
        await self._session.execute(stmt)

    async def delete(
        self,
        user_id: uuid.UUID,
        broker: str,
    ) -> None:
        """Delete a broker connection for the given user and broker.

        If no matching row exists, this is a no-op (no error is raised).
        The caller should check for existence first when an error is desired.

        Args:
            user_id: UUID of the owning user.
            broker: Broker identifier (e.g. ``"schwab"``).
        """
        stmt = delete(BrokerConnection).where(
            BrokerConnection.user_id == user_id,
            BrokerConnection.broker == broker,
        )
        await self._session.execute(stmt)
