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
    settings.database_url,
    echo=(settings.environment == "development"),
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


async def get_session() -> AsyncGenerator[AsyncSession, None]:
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
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
