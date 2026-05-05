"""Repository for check-in field definition persistence."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.daily_checkin import (
    CheckinFieldDefinition,
    FieldTypeEnum,
)


class CheckinFieldDefinitionRepository:
    """Data-access operations for check-in field definitions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        user_id: uuid.UUID,
        field_name: str,
        field_type: FieldTypeEnum,
    ) -> CheckinFieldDefinition:
        """Create and flush a new check-in field definition."""
        model = CheckinFieldDefinition(
            user_id=user_id,
            field_name=field_name,
            field_type=field_type,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def get_by_id(
        self,
        definition_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> CheckinFieldDefinition | None:
        """Return a user-scoped definition by id."""
        result = await self._session.execute(
            select(CheckinFieldDefinition).where(
                CheckinFieldDefinition.id == definition_id,
                CheckinFieldDefinition.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        is_active: bool | None = None,
    ) -> Sequence[CheckinFieldDefinition]:
        """List user definitions ordered by creation time."""
        stmt = (
            select(CheckinFieldDefinition)
            .where(CheckinFieldDefinition.user_id == user_id)
            .order_by(CheckinFieldDefinition.created_at.asc())
        )
        if is_active is not None:
            stmt = stmt.where(CheckinFieldDefinition.is_active == is_active)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def update(
        self,
        model: CheckinFieldDefinition,
        field_name: str | None = None,
        is_active: bool | None = None,
    ) -> CheckinFieldDefinition:
        """Update and flush a definition."""
        if field_name is not None:
            model.field_name = field_name
        if is_active is not None:
            model.is_active = is_active
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def get_by_name_and_user(
        self,
        user_id: uuid.UUID,
        field_name: str,
    ) -> CheckinFieldDefinition | None:
        """Return a definition by stable name for a user."""
        result = await self._session.execute(
            select(CheckinFieldDefinition).where(
                CheckinFieldDefinition.user_id == user_id,
                CheckinFieldDefinition.field_name == field_name,
            )
        )
        return result.scalar_one_or_none()

    async def delete(self, model: CheckinFieldDefinition) -> None:
        """Delete a field definition model."""
        await self._session.delete(model)
        await self._session.flush()

    async def seed_defaults(self, user_id: uuid.UUID) -> None:
        """Insert default field definitions if they do not exist."""
        defaults = [
            {"field_name": "mood-level", "field_type": FieldTypeEnum.INTEGER.value},
            {"field_name": "focus", "field_type": FieldTypeEnum.INTEGER.value},
            {
                "field_name": "rule-followed",
                "field_type": FieldTypeEnum.BOOLEAN.value,
            },
        ]
        stmt = pg_insert(CheckinFieldDefinition).values(
            [
                {
                    "user_id": user_id,
                    "field_name": row["field_name"],
                    "field_type": row["field_type"],
                    "is_active": True,
                }
                for row in defaults
            ]
        )
        stmt = stmt.on_conflict_do_nothing(
            constraint="uq_checkin_field_user_name",
        )
        await self._session.execute(stmt)
        await self._session.flush()
