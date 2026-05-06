"""Service layer for check-in field definition operations."""

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    CheckinFieldDefinitionNotFoundError,
    CheckinFieldDefinitionValidationError,
)
from app.repositories.checkin_field_definition_repository import (
    CheckinFieldDefinitionRepository,
)
from app.schemas.daily_checkin import (
    CheckinFieldDefinitionCreate,
    CheckinFieldDefinitionRead,
    CheckinFieldDefinitionUpdate,
)


class CheckinFieldDefinitionService:
    """Business rules for check-in field definitions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = CheckinFieldDefinitionRepository(session)

    async def create_field(
        self,
        user_id: uuid.UUID,
        payload: CheckinFieldDefinitionCreate,
    ) -> CheckinFieldDefinitionRead:
        """Create a new field definition with uniqueness enforcement."""
        existing = await self._repo.get_by_name_and_user(user_id, payload.field_name)
        if existing is not None:
            raise CheckinFieldDefinitionValidationError(
                "field_name already exists for this user"
            )
        try:
            model = await self._repo.create(
                user_id=user_id,
                field_name=payload.field_name,
                field_type=payload.field_type,
            )
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise CheckinFieldDefinitionValidationError(
                "field_name already exists for this user"
            ) from exc
        return CheckinFieldDefinitionRead.model_validate(model)

    async def list_fields(
        self,
        user_id: uuid.UUID,
        is_active: bool | None = None,
    ) -> list[CheckinFieldDefinitionRead]:
        """List user field definitions with optional activity filter."""
        models = await self._repo.list_by_user(user_id=user_id, is_active=is_active)
        return [CheckinFieldDefinitionRead.model_validate(model) for model in models]

    async def update_field(
        self,
        user_id: uuid.UUID,
        field_id: uuid.UUID,
        payload: CheckinFieldDefinitionUpdate,
    ) -> CheckinFieldDefinitionRead:
        """Update mutable field-definition columns only."""
        model = await self._repo.get_by_id(definition_id=field_id, user_id=user_id)
        if model is None:
            raise CheckinFieldDefinitionNotFoundError(
                "check-in field definition not found"
            )

        try:
            updated = await self._repo.update(
                model=model,
                is_active=payload.is_active,
            )
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise CheckinFieldDefinitionValidationError(
                "field_name already exists for this user"
            ) from exc
        return CheckinFieldDefinitionRead.model_validate(updated)

    async def delete_field(self, user_id: uuid.UUID, field_id: uuid.UUID) -> None:
        """Delete one field definition by id for the requesting user."""
        model = await self._repo.get_by_id(definition_id=field_id, user_id=user_id)
        if model is None:
            raise CheckinFieldDefinitionNotFoundError(
                "check-in field definition not found"
            )

        await self._repo.delete(model)
        await self._session.commit()
