"""Service layer for check-in field definition operations."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

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
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="field_name already exists for this user",
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
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="field_name already exists for this user",
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="check-in field definition not found",
            )

        if payload.field_name is not None and payload.field_name != model.field_name:
            existing = await self._repo.get_by_name_and_user(
                user_id, payload.field_name
            )
            if existing is not None and existing.id != model.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="field_name already exists for this user",
                )

        try:
            updated = await self._repo.update(
                model=model,
                field_name=payload.field_name,
                is_active=payload.is_active,
            )
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="field_name already exists for this user",
            ) from exc
        return CheckinFieldDefinitionRead.model_validate(updated)
