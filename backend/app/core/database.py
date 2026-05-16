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

"""Async SQLAlchemy engine, session factory, and FastAPI dependency."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Declarative base class for all ORM models.

    All SQLAlchemy ORM models must inherit from this class so that
    Alembic's autogenerate can discover them automatically.
    """


# ---------------------------------------------------------------------------
# Engine & session factory
# ---------------------------------------------------------------------------

engine = create_async_engine(
    settings.async_database_url,
    echo=False,  # disabled in dev to reduce noise (use DB log level instead)
    pool_pre_ping=True,
)
"""Async SQLAlchemy engine created from ``DATABASE_URL``."""

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
"""Session factory used by :func:`get_session` and test fixtures."""


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


async def get_session() -> AsyncGenerator[AsyncSession]:
    """Yield an :class:`AsyncSession` for use in FastAPI dependencies.

    The session is committed on clean exit and rolled back on any
    exception, then always closed.

    Yields:
        An open :class:`AsyncSession` bound to the configured engine.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:  # Re-raise after rollback — caller sees original exception
            await session.rollback()
            raise
        finally:
            await session.close()
