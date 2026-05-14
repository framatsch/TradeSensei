import datetime as dt
import uuid
from typing import Literal

from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.model_book_repository import ModelBookRepository
from app.schemas.model_book import ModelBookEntriesPage, ModelBookEntryResponse


class ModelBookService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = ModelBookRepository(session)

    async def get_entries(
        self,
        user_id: uuid.UUID,
        entity_type: Literal["trade", "checkin", "all"],
        from_date: dt.date | None,
        to_date: dt.date | None,
        page: int,
        per_page: int,
    ) -> ModelBookEntriesPage:
        items, total = await self.repo.get_entries(
            user_id=user_id,
            entity_type=entity_type,
            from_date=from_date,
            to_date=to_date,
            page=page,
            per_page=per_page,
        )

        parsed_items: list[ModelBookEntryResponse] = []
        for item in items:
            # Pydantic will validate depending on type
            parsed_items.append(TypeAdapter(ModelBookEntryResponse).validate_python(item))

        return ModelBookEntriesPage(
            items=parsed_items,
            total=total,
            page=page,
            per_page=per_page,
            next_cursor=None,
        )
