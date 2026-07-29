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

"""MCP transport endpoints secured by personal access tokens."""

import asyncio
import base64
import json
import logging
import re
import uuid
from collections.abc import AsyncGenerator
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, ValidationError, model_validator
from sqlalchemy import and_, func, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from app.core.config import settings
from app.core.constants import (
    EMOTION_MAX_LENGTH,
    JOURNAL_MAX_LENGTH,
    MCP_ATTACHMENT_MAX_INLINE_BYTES,
    MCP_ATTACHMENT_MAX_ITEMS,
    NOTE_MAX_LENGTH,
)
from app.core.database import get_session
from app.core.deps import get_current_user_from_pat
from app.core.exceptions import (
    AnnotationDefinitionNotFoundError,
    AnnotationDefinitionValidationError,
    NoteNotFoundError,
    TaxonomyNotFoundError,
    TaxonomyValidationError,
    TradeNotFoundError,
)
from app.models.account import Account, AccountType
from app.models.annotation_definition import AnnotationDefinition
from app.models.checkin_annotation import CheckinAnnotation
from app.models.checkin_taxonomy import CheckinTaxonomy
from app.models.daily_checkin import DailyCheckin
from app.models.playbook import Playbook
from app.models.playbook_taxonomy import PlaybookTaxonomy
from app.models.portfolio import Portfolio
from app.models.taxonomy import Taxonomy
from app.models.trade import AssetClass, Trade
from app.models.trade_annotation import TradeAnnotation
from app.models.trade_taxonomy import TradeTaxonomy
from app.models.user import User
from app.repositories._annotation_filter import apply_annotation_filters as _apply_annotation_filters
from app.schemas.annotation_definition import AnnotationDefinitionCreate, AnnotationDefinitionUpdate
from app.schemas.annotation_filter import AnnotationFilterItem
from app.schemas.note import TradeNoteCreate, TradeNoteUpdate
from app.schemas.taxonomy import TaxonomyCreate, TaxonomyUpdate
from app.schemas.trade import TradeUpdate
from app.services.annotation_definition_service import AnnotationDefinitionService
from app.services.audit_service import AuditEventService, generate_request_id
from app.services.note_service import NoteService
from app.services.playbook_taxonomy_service import PlaybookTaxonomyService
from app.services.storage_service import StorageService
from app.services.taxonomy_service import TaxonomyService
from app.services.trade_service import TradeService
from app.utils.annotation_mapping import map_value_to_column
from app.utils.scope_utils import scope_contains

router = APIRouter(prefix="/mcp", tags=["mcp"])
logger = logging.getLogger(__name__)

_KEEPALIVE_INTERVAL = 15

# Maps session_id → (owner_user_id, message_queue). Storing the owner allows
# mcp_messages to reject cross-user POSTs without a DB lookup.
_ACTIVE_STREAMS: dict[str, tuple[uuid.UUID, asyncio.Queue[str]]] = {}


async def _get_mcp_session_with_rls(
    current_user: Annotated[User, Depends(get_current_user_from_pat)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AsyncGenerator[tuple[User, AsyncSession]]:
    uid = str(current_user.id)
    # asyncpg/psycopg do not support parameterised SET LOCAL statements, so an
    # f-string is the only option. `uid` is always a UUID (hex chars + dashes),
    # making SQL injection impossible here. Same pattern as get_session_with_rls
    # in deps.py.
    await session.execute(
        text(f"SET LOCAL app.current_user_id = '{uid}'")  # noqa: S608
    )
    yield current_user, session


class AdvancedTradeSearchParams(BaseModel):
    date_from: datetime | None = None
    date_to: datetime | None = None
    symbol: str | None = Field(default=None, max_length=50)
    asset_class: AssetClass | None = None
    pnl_min: Decimal | None = None
    pnl_max: Decimal | None = None
    taxonomy_ids: list[uuid.UUID] = Field(default_factory=list, max_length=50)
    annotation_filters: list[AnnotationFilterItem] | None = None
    portfolio_id: uuid.UUID | None = None
    sort_by: str | None = Field(default="opened_at", description="Field to sort by (e.g. pnl, opened_at)")
    sort_dir: str | None = Field(default="desc", description="Sort direction (asc or desc)")
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_annotation_primary_filter(self) -> "AdvancedTradeSearchParams":
        if self.annotation_filters and not (self.symbol or (self.date_from and self.date_to)):
            raise ValueError(
                "annotation_filters require either a symbol or both date_from and date_to",
            )
        return self


class SyncAnnotationInput(BaseModel):
    annotation_definition_id: uuid.UUID
    value: int | float | bool | str


class SyncTradeMetadataParams(BaseModel):
    trade_ids: list[uuid.UUID]
    journal: str | None = None
    taxonomy_ids: list[uuid.UUID] | None = None
    annotations: list[SyncAnnotationInput] | None = None

    @model_validator(mode="after")
    def validate_max_trade_ids(self) -> "SyncTradeMetadataParams":
        if len(self.trade_ids) > 50:
            raise ValueError("Maximum 50 trade IDs per call")
        return self


class CreateStrategyPlaybookParams(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    target_winrate: float | None = Field(default=None, ge=0.0, le=1.0)


class UpdateStrategyPlaybookParams(BaseModel):
    playbook_id: uuid.UUID
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    taxonomy_ids: list[uuid.UUID] | None = None
    target_winrate: float | None = Field(default=None, ge=0.0, le=1.0)
    is_active: bool | None = None


class GetStrategyPlaybookParams(BaseModel):
    playbook_id: uuid.UUID


class ListCheckinsParams(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    taxonomy_ids: list[uuid.UUID] = Field(default_factory=list, max_length=50)
    annotation_filters: list[AnnotationFilterItem] | None = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class SyncCheckinMetadataParams(BaseModel):
    checkin_ids: list[uuid.UUID]
    taxonomy_ids: list[uuid.UUID] | None = None
    annotations: list[SyncAnnotationInput] | None = None

    @model_validator(mode="after")
    def validate_max_checkin_ids(self) -> "SyncCheckinMetadataParams":
        if len(self.checkin_ids) > 50:
            raise ValueError("Maximum 50 checkin IDs per call")
        return self


class SyncPlaybookMetadataParams(BaseModel):
    playbook_id: uuid.UUID
    taxonomy_ids: list[uuid.UUID]


class ListAccountsParams(BaseModel):
    portfolio_id: uuid.UUID | None = None
    broker: str | None = Field(default=None, max_length=50)


class CreateTaxonomyParams(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    scope: str
    color_hex: str
    description: str | None = Field(default=None, max_length=500)
    icon_identifier: str | None = Field(default=None, max_length=100)


class UpdateTaxonomyParams(BaseModel):
    taxonomy_id: uuid.UUID
    name: str | None = Field(default=None, min_length=1, max_length=100)
    scope: str | None = None
    color_hex: str | None = None
    description: str | None = Field(default=None, max_length=500)
    icon_identifier: str | None = Field(default=None, max_length=100)
    is_archived: bool | None = None


class DeleteTaxonomyParams(BaseModel):
    taxonomy_id: uuid.UUID


class CreateAnnotationDefinitionParams(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: Literal["int", "float", "bool", "string_enum"]
    scope: str
    description: str | None = Field(default=None, max_length=500)
    icon_identifier: str | None = Field(default=None, max_length=100)
    scale_labels: dict[str, Any] | None = None


class UpdateAnnotationDefinitionParams(BaseModel):
    annotation_definition_id: uuid.UUID
    name: str | None = Field(default=None, min_length=1, max_length=100)
    type: Literal["int", "float", "bool", "string_enum"] | None = None
    scope: str | None = None
    description: str | None = Field(default=None, max_length=500)
    icon_identifier: str | None = Field(default=None, max_length=100)
    scale_labels: dict[str, Any] | None = None
    is_archived: bool | None = None


class DeleteAnnotationDefinitionParams(BaseModel):
    annotation_definition_id: uuid.UUID


class GetTradeParams(BaseModel):
    trade_id: uuid.UUID


class GetCheckinParams(BaseModel):
    checkin_id: uuid.UUID


class GetTaxonomyParams(BaseModel):
    taxonomy_id: uuid.UUID


class GetAnnotationDefinitionParams(BaseModel):
    annotation_definition_id: uuid.UUID


class AddTradeNoteParams(BaseModel):
    trade_id: uuid.UUID
    content: str = Field(min_length=1, max_length=NOTE_MAX_LENGTH)
    emotion: str | None = Field(default=None, max_length=EMOTION_MAX_LENGTH)


class UpdateTradeNoteParams(BaseModel):
    trade_id: uuid.UUID
    note_id: uuid.UUID
    content: str | None = Field(default=None, min_length=1, max_length=NOTE_MAX_LENGTH)
    emotion: str | None = Field(default=None, max_length=EMOTION_MAX_LENGTH)


class DeleteTradeNoteParams(BaseModel):
    trade_id: uuid.UUID
    note_id: uuid.UUID


class UpdateTradeJournalParams(BaseModel):
    trade_id: uuid.UUID
    text: str = Field(max_length=JOURNAL_MAX_LENGTH)
    mode: Literal["replace", "append"] = "replace"


class GetTradeAttachmentsParams(BaseModel):
    trade_id: uuid.UUID
    format: Literal["image", "url"] = "image"
    max_items: int = Field(default=MCP_ATTACHMENT_MAX_ITEMS, ge=1, le=MCP_ATTACHMENT_MAX_ITEMS)


class GetPlaybookAttachmentsParams(BaseModel):
    playbook_id: uuid.UUID
    format: Literal["image", "url"] = "image"
    max_items: int = Field(default=MCP_ATTACHMENT_MAX_ITEMS, ge=1, le=MCP_ATTACHMENT_MAX_ITEMS)


class LinkTradePlaybookParams(BaseModel):
    trade_id: uuid.UUID
    playbook_id: uuid.UUID | None = None
    clear: bool = False

    @model_validator(mode="after")
    def validate_target(self) -> "LinkTradePlaybookParams":
        if not self.clear and self.playbook_id is None:
            raise ValueError("playbook_id is required unless clear is true")
        return self


def _tool_error(code: int, message: str) -> dict[str, Any]:
    return {"code": code, "message": message}


def _serialize_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _serialize_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _annotation_typed_value(
    value_int: int | None,
    value_float: Decimal | None,
    value_bool: bool | None,
    value_string: str | None,
) -> int | float | bool | str | None:
    """Resolve the single populated typed value column on an annotation assignment."""
    if value_bool is not None:
        return value_bool
    if value_int is not None:
        return value_int
    if value_float is not None:
        return float(value_float)
    if value_string is not None:
        return value_string
    return None


_STORAGE_REF_FILENAME_RE = re.compile(r"^\d{8}T\d{6}-[0-9a-f-]{36}-(?P<name>.+)$")


def _filename_from_storage_ref(storage_ref: str) -> str:
    """Extract the human-readable filename from a storage ref.

    Storage keys are written as ``{prefix}{user_id}/{timestamp}-{uuid}-{name}``.
    Falls back to the raw path segment if the expected pattern isn't found.
    """
    segment = storage_ref.rsplit("/", 1)[-1]
    match = _STORAGE_REF_FILENAME_RE.match(segment)
    return match.group("name") if match else segment


def _build_image_content_block(data: bytes, mime_type: str) -> dict[str, Any]:
    return {
        "type": "image",
        "data": base64.b64encode(data).decode("ascii"),
        "mimeType": mime_type,
    }


def _build_text_content_block(text: str) -> dict[str, Any]:
    return {"type": "text", "text": text}


async def _handle_get_metadata_schema(
    user_id: uuid.UUID,
    db: AsyncSession,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    del arguments
    taxonomy_result = await db.execute(
        select(Taxonomy).where(Taxonomy.user_id == user_id, Taxonomy.is_archived.is_(False)).order_by(Taxonomy.name.asc()),
    )
    annotation_result = await db.execute(
        select(AnnotationDefinition)
        .where(
            AnnotationDefinition.user_id == user_id,
            AnnotationDefinition.is_archived.is_(False),
        )
        .order_by(AnnotationDefinition.name.asc()),
    )

    taxonomies = [
        {
            "id": str(item.id),
            "name": item.name,
            "scope": item.scope,
            "color_hex": item.color_hex,
            "description": item.description,
        }
        for item in taxonomy_result.scalars().all()
    ]
    annotation_definitions = [
        {
            "id": str(item.id),
            "name": item.name,
            "type": item.type,
            "scope": item.scope,
            "scale_labels": item.scale_labels,
            "description": item.description,
        }
        for item in annotation_result.scalars().all()
    ]

    return {
        "taxonomies": taxonomies,
        "annotation_definitions": annotation_definitions,
    }


async def _handle_search_trades_advanced(
    user_id: uuid.UUID,
    db: AsyncSession,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    params = AdvancedTradeSearchParams.model_validate(arguments)

    query = select(Trade).where(Trade.user_id == user_id)

    if params.date_from is not None:
        query = query.where(Trade.opened_at >= params.date_from)
    if params.date_to is not None:
        query = query.where(Trade.opened_at <= params.date_to)
    if params.symbol:
        query = query.where(Trade.symbol.ilike(f"%{params.symbol}%"))
    if params.asset_class is not None:
        query = query.where(Trade.asset_class == params.asset_class)
    if params.pnl_min is not None:
        query = query.where(Trade.pnl >= params.pnl_min)
    if params.pnl_max is not None:
        query = query.where(Trade.pnl <= params.pnl_max)

    for taxonomy_id in params.taxonomy_ids:
        taxonomy_alias = aliased(TradeTaxonomy)
        query = query.join(
            taxonomy_alias,
            and_(
                taxonomy_alias.trade_id == Trade.id,
                taxonomy_alias.taxonomy_id == taxonomy_id,
            ),
        )

    if params.annotation_filters:
        query = _apply_annotation_filters(
            query,
            TradeAnnotation,
            TradeAnnotation.trade_id,
            Trade.id,
            user_id,
            params.annotation_filters,
        )

    if params.portfolio_id is not None:
        query = query.join(Account, Trade.account_id == Account.id).where(
            Account.portfolio_id == params.portfolio_id,
        )

    count_query = select(func.count()).select_from(query.with_only_columns(Trade.id).order_by(None).subquery())
    total_result = await db.execute(count_query)
    total = int(total_result.scalar_one())

    if params.sort_by == "pnl":
        sort_col: Any = Trade.pnl
    elif params.sort_by == "net_pnl":
        sort_col = Trade.net_pnl
    elif params.sort_by == "closed_at":
        sort_col = Trade.closed_at
    else:
        sort_col = Trade.opened_at

    if params.sort_dir == "asc":
        query = query.order_by(sort_col.asc().nulls_last(), Trade.id.asc())
    else:
        query = query.order_by(sort_col.desc().nulls_last(), Trade.id.desc())

    paginated_query = query.limit(params.limit).offset(params.offset)
    result = await db.execute(paginated_query)
    trades = result.scalars().all()

    return {
        "trades": [
            {
                "id": str(trade.id),
                "symbol": trade.symbol,
                "direction": trade.direction.value,
                "asset_class": trade.asset_class.value if trade.asset_class else None,
                "opened_at": _serialize_datetime(trade.opened_at),
                "closed_at": _serialize_datetime(trade.closed_at),
                "pnl": _serialize_decimal(trade.pnl),
                "net_pnl": _serialize_decimal(trade.net_pnl),
                "playbook_id": str(trade.playbook_id) if trade.playbook_id else None,
            }
            for trade in trades
        ],
        "total": total,
        "limit": params.limit,
        "offset": params.offset,
    }


async def _handle_sync_trade_metadata(
    user_id: uuid.UUID,
    db: AsyncSession,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    params = SyncTradeMetadataParams.model_validate(arguments)

    owned_result = await db.execute(
        select(Trade.id).where(Trade.user_id == user_id, Trade.id.in_(params.trade_ids)),
    )
    owned_trade_ids = list(owned_result.scalars().all())

    if not owned_trade_ids:
        return {"updated_count": 0}

    if params.journal is not None:
        await db.execute(
            update(Trade).where(Trade.id.in_(owned_trade_ids)).values(journal=params.journal),
        )

    if params.taxonomy_ids is not None:
        taxonomy_result = await db.execute(
            select(Taxonomy.id).where(
                Taxonomy.user_id == user_id,
                Taxonomy.is_archived.is_(False),
                Taxonomy.id.in_(params.taxonomy_ids),
            ),
        )
        valid_taxonomy_ids = set(taxonomy_result.scalars().all())
        if len(valid_taxonomy_ids) != len(set(params.taxonomy_ids)):
            raise ValueError("One or more taxonomy_ids are invalid for this user")

        for trade_id in owned_trade_ids:
            for taxonomy_id in params.taxonomy_ids:
                insert_stmt = (
                    pg_insert(TradeTaxonomy)
                    .values(trade_id=trade_id, taxonomy_id=taxonomy_id)
                    .on_conflict_do_nothing(
                        constraint="uq_trade_taxonomy_pair",
                    )
                )
                await db.execute(insert_stmt)

    if params.annotations is not None:
        definition_ids = [entry.annotation_definition_id for entry in params.annotations]
        definition_result = await db.execute(
            select(AnnotationDefinition).where(
                AnnotationDefinition.user_id == user_id,
                AnnotationDefinition.is_archived.is_(False),
                AnnotationDefinition.id.in_(definition_ids),
            ),
        )
        definitions = {item.id: item for item in definition_result.scalars().all()}
        if len(definitions) != len(set(definition_ids)):
            raise ValueError("One or more annotations use invalid annotation_definition_id")

        for trade_id in owned_trade_ids:
            for entry in params.annotations:
                definition = definitions[entry.annotation_definition_id]
                typed_values = map_value_to_column(
                    definition.type,
                    entry.value,
                    definition.scale_labels,
                )
                insert_stmt = (
                    pg_insert(TradeAnnotation)
                    .values(
                        trade_id=trade_id,
                        annotation_definition_id=entry.annotation_definition_id,
                        **typed_values,
                    )
                    .on_conflict_do_update(
                        constraint="uq_trade_annotation_pair",
                        set_=typed_values,
                    )
                )
                await db.execute(insert_stmt)

    await db.flush()

    AuditEventService().create_audit_event(
        action="trade.bulk_metadata_synced",
        user_id=user_id,
        email=None,
        resource_type="trade",
        resource_id=None,
        ip_address=None,
        user_agent="mcp",
        request_id=generate_request_id(),
        status_code=200,
        method="POST",
        path="/mcp/messages",
        metadata={"user_id": str(user_id), "trade_count": len(owned_trade_ids)},
    )

    return {"updated_count": len(owned_trade_ids)}


async def _apply_playbook_taxonomies(
    db: AsyncSession,
    user_id: uuid.UUID,
    playbook_id: uuid.UUID,
    taxonomy_ids: list[uuid.UUID],
) -> int:
    owned_playbook = await db.execute(
        select(Playbook.id).where(Playbook.user_id == user_id, Playbook.id == playbook_id),
    )
    if owned_playbook.scalar_one_or_none() is None:
        raise ValueError(f"Playbook {playbook_id} not found")

    if not taxonomy_ids:
        return 0

    taxonomy_result = await db.execute(
        select(Taxonomy).where(
            Taxonomy.user_id == user_id,
            Taxonomy.is_archived.is_(False),
            Taxonomy.id.in_(taxonomy_ids),
        ),
    )
    valid_taxonomies = {item.id: item for item in taxonomy_result.scalars().all()}
    if len(valid_taxonomies) != len(set(taxonomy_ids)):
        raise ValueError("One or more taxonomy_ids are invalid for this user")

    for taxonomy in valid_taxonomies.values():
        if not scope_contains(taxonomy.scope, "playbook"):
            raise ValueError("One or more taxonomy_ids have scope incompatible with playbooks")

    for taxonomy_id in taxonomy_ids:
        insert_stmt = (
            pg_insert(PlaybookTaxonomy).values(playbook_id=playbook_id, taxonomy_id=taxonomy_id).on_conflict_do_nothing(constraint="uq_playbook_taxonomy_pair")
        )
        await db.execute(insert_stmt)

    return len(set(taxonomy_ids))


async def _handle_create_strategy_playbook(
    user_id: uuid.UUID,
    db: AsyncSession,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    params = CreateStrategyPlaybookParams.model_validate(arguments)

    duplicate_check = await db.execute(
        select(Playbook.id).where(Playbook.user_id == user_id, Playbook.name == params.name),
    )
    if duplicate_check.scalar_one_or_none() is not None:
        raise ValueError("A playbook with that name already exists")

    playbook = Playbook(
        user_id=user_id,
        name=params.name,
        description=params.description,
        target_winrate=(Decimal(str(params.target_winrate)) if params.target_winrate is not None else None),
        is_active=True,
    )
    db.add(playbook)
    await db.flush()

    AuditEventService().create_audit_event(
        action="playbook.created",
        user_id=user_id,
        email=None,
        resource_type="playbook",
        resource_id=playbook.id,
        ip_address=None,
        user_agent="mcp",
        request_id=generate_request_id(),
        status_code=200,
        method="POST",
        path="/mcp/messages",
        metadata={"user_id": str(user_id), "playbook_id": str(playbook.id)},
    )

    return {"playbook_id": str(playbook.id), "name": playbook.name}


async def _handle_update_strategy_playbook(
    user_id: uuid.UUID,
    db: AsyncSession,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    params = UpdateStrategyPlaybookParams.model_validate(arguments)

    result = await db.execute(
        select(Playbook).where(Playbook.user_id == user_id, Playbook.id == params.playbook_id),
    )
    playbook = result.scalar_one_or_none()
    if not playbook:
        raise ValueError(f"Playbook {params.playbook_id} not found")

    if params.name is not None and params.name != playbook.name:
        duplicate_check = await db.execute(
            select(Playbook.id).where(Playbook.user_id == user_id, Playbook.name == params.name),
        )
        if duplicate_check.scalar_one_or_none() is not None:
            raise ValueError("A playbook with that name already exists")

    if params.taxonomy_ids is not None:
        await _apply_playbook_taxonomies(
            db=db,
            user_id=user_id,
            playbook_id=params.playbook_id,
            taxonomy_ids=params.taxonomy_ids,
        )

    if params.name is not None and params.name != playbook.name:
        playbook.name = params.name

    if params.description is not None:
        playbook.description = params.description

    if params.target_winrate is not None:
        playbook.target_winrate = Decimal(str(params.target_winrate))

    if params.is_active is not None:
        playbook.is_active = params.is_active

    await db.flush()

    AuditEventService().create_audit_event(
        action="playbook.updated",
        user_id=user_id,
        email=None,
        resource_type="playbook",
        resource_id=playbook.id,
        ip_address=None,
        user_agent="mcp",
        request_id=generate_request_id(),
        status_code=200,
        method="POST",
        path="/mcp/messages",
        metadata={"user_id": str(user_id), "playbook_id": str(playbook.id)},
    )

    return {"playbook_id": str(playbook.id), "name": playbook.name, "is_active": playbook.is_active}


async def _handle_list_strategy_playbooks(
    user_id: uuid.UUID,
    db: AsyncSession,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    del arguments
    result = await db.execute(
        select(Playbook).where(Playbook.user_id == user_id).order_by(Playbook.name.asc()),
    )
    playbooks = result.scalars().all()
    playbook_taxonomy_service = PlaybookTaxonomyService(db)

    enriched_playbooks: list[dict[str, Any]] = []
    for playbook in playbooks:
        taxonomy_assignments = await playbook_taxonomy_service.list(
            playbook_id=playbook.id,
            user_id=user_id,
        )
        enriched_playbooks.append(
            {
                "id": str(playbook.id),
                "name": playbook.name,
                "description": playbook.description,
                "target_winrate": _serialize_decimal(playbook.target_winrate),
                "is_active": playbook.is_active,
                "created_at": _serialize_datetime(playbook.created_at),
                "taxonomy_assignments": [{"taxonomy_id": str(item.id), "name": item.name} for item in taxonomy_assignments],
            }
        )

    return {
        "playbooks": enriched_playbooks,
    }


async def _handle_get_strategy_playbook(
    user_id: uuid.UUID,
    db: AsyncSession,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    params = GetStrategyPlaybookParams.model_validate(arguments)
    result = await db.execute(
        select(Playbook).where(Playbook.user_id == user_id, Playbook.id == params.playbook_id),
    )
    p = result.scalar_one_or_none()
    if not p:
        raise ValueError(f"Playbook {params.playbook_id} not found")

    playbook_taxonomy_service = PlaybookTaxonomyService(db)
    taxonomy_assignments = await playbook_taxonomy_service.list(
        playbook_id=p.id,
        user_id=user_id,
    )

    return {
        "id": str(p.id),
        "name": p.name,
        "description": p.description,
        "target_winrate": _serialize_decimal(p.target_winrate),
        "is_active": p.is_active,
        "created_at": _serialize_datetime(p.created_at),
        "updated_at": _serialize_datetime(p.updated_at),
        "taxonomy_assignments": [{"taxonomy_id": str(item.id), "name": item.name} for item in taxonomy_assignments],
    }


async def _handle_sync_playbook_metadata(
    user_id: uuid.UUID,
    db: AsyncSession,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    params = SyncPlaybookMetadataParams.model_validate(arguments)

    updated_count = await _apply_playbook_taxonomies(
        db=db,
        user_id=user_id,
        playbook_id=params.playbook_id,
        taxonomy_ids=params.taxonomy_ids,
    )

    await db.flush()

    AuditEventService().create_audit_event(
        action="playbook.bulk_metadata_synced",
        user_id=user_id,
        email=None,
        resource_type="playbook",
        resource_id=params.playbook_id,
        ip_address=None,
        user_agent="mcp",
        request_id=generate_request_id(),
        status_code=200,
        method="POST",
        path="/mcp/messages",
        metadata={
            "user_id": str(user_id),
            "playbook_id": str(params.playbook_id),
            "taxonomy_count": len(set(params.taxonomy_ids)),
        },
    )

    return {"updated_count": updated_count}


async def _handle_list_portfolios(
    user_id: uuid.UUID,
    db: AsyncSession,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    del arguments
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user_id).order_by(Portfolio.name.asc()),
    )
    portfolios = result.scalars().all()
    return {
        "portfolios": [
            {
                "id": str(p.id),
                "name": p.name,
                "base_currency": p.base_currency,
            }
            for p in portfolios
        ],
    }


def _mask_account_number(account_number: str | None) -> str | None:
    if account_number is None or len(account_number) <= 4:
        return account_number
    return f"****{account_number[-4:]}"


async def _handle_list_accounts(
    user_id: uuid.UUID,
    db: AsyncSession,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    params = ListAccountsParams.model_validate(arguments)

    query = select(Account).where(Account.user_id == user_id, Account.is_active.is_(True))

    if params.portfolio_id is not None:
        query = query.where(Account.portfolio_id == params.portfolio_id)
    if params.broker is not None:
        query = query.where(Account.type == AccountType(params.broker))

    query = query.order_by(Account.name.asc())
    result = await db.execute(query)
    accounts = result.scalars().all()

    return {
        "accounts": [
            {
                "id": str(a.id),
                "name": a.name,
                "broker": a.type.value,
                "account_number_masked": _mask_account_number(a.account_number),
                "currency": a.currency,
                "portfolio_id": str(a.portfolio_id) if a.portfolio_id else None,
            }
            for a in accounts
        ],
    }


async def _handle_list_checkins(
    user_id: uuid.UUID,
    db: AsyncSession,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    params = ListCheckinsParams.model_validate(arguments)

    query = (
        select(DailyCheckin)
        .where(DailyCheckin.user_id == user_id)
        .options(
            selectinload(DailyCheckin.taxonomy_assignments).selectinload(CheckinTaxonomy.taxonomy),
            selectinload(DailyCheckin.annotation_assignments).selectinload(CheckinAnnotation.annotation_definition),
        )
    )

    if params.date_from is not None:
        query = query.where(DailyCheckin.date >= params.date_from)
    if params.date_to is not None:
        query = query.where(DailyCheckin.date <= params.date_to)

    # MCP uses AND semantics for taxonomy_ids (strict intersection):
    # the checkin must have ALL requested tags, not just any one of them.
    if params.taxonomy_ids:
        for taxonomy_id in params.taxonomy_ids:
            taxonomy_alias = aliased(CheckinTaxonomy)
            query = query.join(
                taxonomy_alias,
                and_(
                    taxonomy_alias.checkin_id == DailyCheckin.id,
                    taxonomy_alias.taxonomy_id == taxonomy_id,
                ),
            )

    if params.annotation_filters:
        query = _apply_annotation_filters(
            query,
            CheckinAnnotation,
            CheckinAnnotation.checkin_id,
            DailyCheckin.id,
            user_id,
            params.annotation_filters,
        )

    count_query = select(func.count()).select_from(query.with_only_columns(DailyCheckin.id).order_by(None).subquery())
    total_result = await db.execute(count_query)
    total = int(total_result.scalar_one())

    query = query.order_by(DailyCheckin.date.desc()).limit(params.limit).offset(params.offset)
    result = await db.execute(query)
    checkins = result.scalars().all()

    def _annotation_value(ann: CheckinAnnotation) -> int | float | bool | str | None:
        if ann.value_bool is not None:
            return ann.value_bool
        if ann.value_int is not None:
            return ann.value_int
        if ann.value_float is not None:
            return float(ann.value_float)
        if ann.value_string is not None:
            return ann.value_string
        return None

    return {
        "checkins": [
            {
                "id": str(c.id),
                "date": c.date.isoformat(),
                "notes": c.notes,
                "taxonomy_assignments": [
                    {"taxonomy_id": str(t.taxonomy_id), "name": t.taxonomy.name if t.taxonomy else None} for t in (c.taxonomy_assignments or [])
                ],
                "annotation_assignments": [
                    {
                        "annotation_definition_id": str(a.annotation_definition_id),
                        "name": a.annotation_definition.name if a.annotation_definition else None,
                        "value": _annotation_value(a),
                    }
                    for a in (c.annotation_assignments or [])
                ],
            }
            for c in checkins
        ],
        "total": total,
        "limit": params.limit,
        "offset": params.offset,
    }


async def _handle_sync_checkin_metadata(
    user_id: uuid.UUID,
    db: AsyncSession,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    params = SyncCheckinMetadataParams.model_validate(arguments)

    owned_result = await db.execute(
        select(DailyCheckin.id).where(DailyCheckin.user_id == user_id, DailyCheckin.id.in_(params.checkin_ids)),
    )
    owned_checkin_ids = list(owned_result.scalars().all())

    if not owned_checkin_ids:
        return {"updated_count": 0}

    if params.taxonomy_ids is not None:
        taxonomy_result = await db.execute(
            select(Taxonomy.id).where(
                Taxonomy.user_id == user_id,
                Taxonomy.is_archived.is_(False),
                Taxonomy.id.in_(params.taxonomy_ids),
            ),
        )
        valid_taxonomy_ids = set(taxonomy_result.scalars().all())
        if len(valid_taxonomy_ids) != len(set(params.taxonomy_ids)):
            raise ValueError("One or more taxonomy_ids are invalid for this user")

        for checkin_id in owned_checkin_ids:
            for taxonomy_id in params.taxonomy_ids:
                insert_stmt = (
                    pg_insert(CheckinTaxonomy)
                    .values(checkin_id=checkin_id, taxonomy_id=taxonomy_id)
                    .on_conflict_do_nothing(constraint="uq_checkin_taxonomy_pair")
                )
                await db.execute(insert_stmt)

    if params.annotations is not None:
        definition_ids = [entry.annotation_definition_id for entry in params.annotations]
        definition_result = await db.execute(
            select(AnnotationDefinition).where(
                AnnotationDefinition.user_id == user_id,
                AnnotationDefinition.is_archived.is_(False),
                AnnotationDefinition.id.in_(definition_ids),
            ),
        )
        definitions = {item.id: item for item in definition_result.scalars().all()}
        if len(definitions) != len(set(definition_ids)):
            raise ValueError("One or more annotations use invalid annotation_definition_id")

        for checkin_id in owned_checkin_ids:
            for entry in params.annotations:
                definition = definitions[entry.annotation_definition_id]
                typed_values = map_value_to_column(
                    definition.type,
                    entry.value,
                    definition.scale_labels,
                )
                insert_stmt = (
                    pg_insert(CheckinAnnotation)
                    .values(
                        checkin_id=checkin_id,
                        annotation_definition_id=entry.annotation_definition_id,
                        **typed_values,
                    )
                    .on_conflict_do_update(
                        constraint="uq_checkin_annotation_pair",
                        set_=typed_values,
                    )
                )
                await db.execute(insert_stmt)

    await db.flush()
    AuditEventService().create_audit_event(
        action="checkin.bulk_metadata_synced",
        user_id=user_id,
        email=None,
        resource_type="checkin",
        resource_id=None,
        ip_address=None,
        user_agent="mcp",
        request_id=generate_request_id(),
        status_code=200,
        method="POST",
        path="/mcp/messages",
        metadata={"user_id": str(user_id), "checkin_count": len(owned_checkin_ids)},
    )

    return {"updated_count": len(owned_checkin_ids)}


async def _handle_create_taxonomy(
    user_id: uuid.UUID,
    db: AsyncSession,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    params = CreateTaxonomyParams.model_validate(arguments)
    service = TaxonomyService(db)

    try:
        taxonomy = await service.create(
            payload=TaxonomyCreate(
                name=params.name,
                scope=params.scope,
                color_hex=params.color_hex,
                description=params.description,
                icon_identifier=params.icon_identifier,
            ),
            user_id=user_id,
        )
    except (TaxonomyNotFoundError, TaxonomyValidationError) as exc:
        raise ValueError(str(exc)) from exc

    AuditEventService().create_audit_event(
        action="taxonomy.created",
        user_id=user_id,
        email=None,
        resource_type="taxonomy",
        resource_id=taxonomy.id,
        ip_address=None,
        user_agent="mcp",
        request_id=generate_request_id(),
        status_code=200,
        method="POST",
        path="/mcp/messages",
        metadata={"user_id": str(user_id), "taxonomy_id": str(taxonomy.id)},
    )

    return {"taxonomy_id": str(taxonomy.id), "name": taxonomy.name}


async def _handle_update_taxonomy(
    user_id: uuid.UUID,
    db: AsyncSession,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    params = UpdateTaxonomyParams.model_validate(arguments)
    service = TaxonomyService(db)

    update_payload_data: dict[str, Any] = {}
    if params.name is not None:
        update_payload_data["name"] = params.name
    if params.scope is not None:
        update_payload_data["scope"] = params.scope
    if params.color_hex is not None:
        update_payload_data["color_hex"] = params.color_hex
    if params.description is not None:
        update_payload_data["description"] = params.description
    if params.icon_identifier is not None:
        update_payload_data["icon_identifier"] = params.icon_identifier

    update_payload = TaxonomyUpdate(**update_payload_data)

    try:
        taxonomy = await service.get(user_id=user_id, taxonomy_id=params.taxonomy_id)
        if update_payload.model_dump(exclude_unset=True):
            taxonomy = await service.update(
                taxonomy_id=params.taxonomy_id,
                payload=update_payload,
                user_id=user_id,
            )

        if params.is_archived is True:
            taxonomy = await service.archive(taxonomy_id=params.taxonomy_id, user_id=user_id)
        elif params.is_archived is False:
            taxonomy = await service.unarchive(taxonomy_id=params.taxonomy_id, user_id=user_id)
    except (TaxonomyNotFoundError, TaxonomyValidationError) as exc:
        raise ValueError(str(exc)) from exc

    AuditEventService().create_audit_event(
        action="taxonomy.updated",
        user_id=user_id,
        email=None,
        resource_type="taxonomy",
        resource_id=taxonomy.id,
        ip_address=None,
        user_agent="mcp",
        request_id=generate_request_id(),
        status_code=200,
        method="POST",
        path="/mcp/messages",
        metadata={"user_id": str(user_id), "taxonomy_id": str(taxonomy.id)},
    )

    return {
        "taxonomy_id": str(taxonomy.id),
        "name": taxonomy.name,
        "is_archived": taxonomy.is_archived,
    }


async def _handle_delete_taxonomy(
    user_id: uuid.UUID,
    db: AsyncSession,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    params = DeleteTaxonomyParams.model_validate(arguments)
    service = TaxonomyService(db)

    try:
        assignment_counts = await service.get_assignment_counts(
            taxonomy_id=params.taxonomy_id,
            user_id=user_id,
        )
        if assignment_counts["total_count"] > 0:
            raise ValueError("has active assignments - remove assignments before deleting")
        taxonomy = await service.archive(taxonomy_id=params.taxonomy_id, user_id=user_id)
    except (TaxonomyNotFoundError, TaxonomyValidationError) as exc:
        raise ValueError(str(exc)) from exc

    AuditEventService().create_audit_event(
        action="taxonomy.deleted",
        user_id=user_id,
        email=None,
        resource_type="taxonomy",
        resource_id=taxonomy.id,
        ip_address=None,
        user_agent="mcp",
        request_id=generate_request_id(),
        status_code=200,
        method="POST",
        path="/mcp/messages",
        metadata={"user_id": str(user_id), "taxonomy_id": str(taxonomy.id)},
    )

    return {"archived": True}


async def _handle_create_annotation_definition(
    user_id: uuid.UUID,
    db: AsyncSession,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    params = CreateAnnotationDefinitionParams.model_validate(arguments)
    service = AnnotationDefinitionService(db)

    try:
        definition = await service.create(
            payload=AnnotationDefinitionCreate(
                name=params.name,
                type=params.type,
                scope=params.scope,
                description=params.description,
                icon_identifier=params.icon_identifier,
                scale_labels=params.scale_labels,
            ),
            user_id=user_id,
        )
    except (AnnotationDefinitionNotFoundError, AnnotationDefinitionValidationError) as exc:
        raise ValueError(str(exc)) from exc

    AuditEventService().create_audit_event(
        action="annotation_definition.created",
        user_id=user_id,
        email=None,
        resource_type="annotation_definition",
        resource_id=definition.id,
        ip_address=None,
        user_agent="mcp",
        request_id=generate_request_id(),
        status_code=200,
        method="POST",
        path="/mcp/messages",
        metadata={
            "user_id": str(user_id),
            "annotation_definition_id": str(definition.id),
        },
    )

    return {
        "annotation_definition_id": str(definition.id),
        "name": definition.name,
        "type": definition.type,
    }


async def _handle_update_annotation_definition(
    user_id: uuid.UUID,
    db: AsyncSession,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    params = UpdateAnnotationDefinitionParams.model_validate(arguments)
    service = AnnotationDefinitionService(db)

    update_payload_data: dict[str, Any] = {}
    if params.name is not None:
        update_payload_data["name"] = params.name
    if params.type is not None:
        update_payload_data["type"] = params.type
    if params.scope is not None:
        update_payload_data["scope"] = params.scope
    if params.description is not None:
        update_payload_data["description"] = params.description
    if params.icon_identifier is not None:
        update_payload_data["icon_identifier"] = params.icon_identifier
    if params.scale_labels is not None:
        update_payload_data["scale_labels"] = params.scale_labels

    update_payload = AnnotationDefinitionUpdate(**update_payload_data)

    try:
        definition = await service.get(
            user_id=user_id,
            definition_id=params.annotation_definition_id,
        )
        if update_payload.model_dump(exclude_unset=True):
            definition = await service.update(
                definition_id=params.annotation_definition_id,
                payload=update_payload,
                user_id=user_id,
            )

        if params.is_archived is True:
            definition = await service.archive(
                definition_id=params.annotation_definition_id,
                user_id=user_id,
            )
        elif params.is_archived is False:
            definition = await service.unarchive(
                definition_id=params.annotation_definition_id,
                user_id=user_id,
            )
    except (AnnotationDefinitionNotFoundError, AnnotationDefinitionValidationError) as exc:
        raise ValueError(str(exc)) from exc

    AuditEventService().create_audit_event(
        action="annotation_definition.updated",
        user_id=user_id,
        email=None,
        resource_type="annotation_definition",
        resource_id=definition.id,
        ip_address=None,
        user_agent="mcp",
        request_id=generate_request_id(),
        status_code=200,
        method="POST",
        path="/mcp/messages",
        metadata={
            "user_id": str(user_id),
            "annotation_definition_id": str(definition.id),
        },
    )

    return {
        "annotation_definition_id": str(definition.id),
        "name": definition.name,
        "is_archived": definition.is_archived,
    }


async def _handle_delete_annotation_definition(
    user_id: uuid.UUID,
    db: AsyncSession,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    params = DeleteAnnotationDefinitionParams.model_validate(arguments)
    service = AnnotationDefinitionService(db)

    try:
        assignment_counts = await service.get_assignment_counts(
            definition_id=params.annotation_definition_id,
            user_id=user_id,
        )
        if assignment_counts["total_count"] > 0:
            raise ValueError("has active assignments - remove assignments before deleting")
        definition = await service.archive(
            definition_id=params.annotation_definition_id,
            user_id=user_id,
        )
    except (AnnotationDefinitionNotFoundError, AnnotationDefinitionValidationError) as exc:
        raise ValueError(str(exc)) from exc

    AuditEventService().create_audit_event(
        action="annotation_definition.deleted",
        user_id=user_id,
        email=None,
        resource_type="annotation_definition",
        resource_id=definition.id,
        ip_address=None,
        user_agent="mcp",
        request_id=generate_request_id(),
        status_code=200,
        method="POST",
        path="/mcp/messages",
        metadata={
            "user_id": str(user_id),
            "annotation_definition_id": str(definition.id),
        },
    )

    return {"archived": True}


async def _handle_get_trade(
    user_id: uuid.UUID,
    db: AsyncSession,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    params = GetTradeParams.model_validate(arguments)

    result = await db.execute(
        select(Trade)
        .where(Trade.user_id == user_id, Trade.id == params.trade_id)
        .options(
            selectinload(Trade.taxonomy_assignments).selectinload(TradeTaxonomy.taxonomy),
            selectinload(Trade.annotation_assignments).selectinload(TradeAnnotation.annotation_definition),
        ),
    )
    trade = result.scalar_one_or_none()
    if trade is None:
        raise ValueError(f"Trade {params.trade_id} not found")

    note_service = NoteService(db)
    notes = await note_service.list_notes(trade_id=trade.id, user_id=user_id)

    return {
        "id": str(trade.id),
        "symbol": trade.symbol,
        "direction": trade.direction.value,
        "asset_class": trade.asset_class.value if trade.asset_class else None,
        "quantity": _serialize_decimal(trade.quantity),
        "entry_price": _serialize_decimal(trade.entry_price),
        "exit_price": _serialize_decimal(trade.exit_price),
        "stop_loss": _serialize_decimal(trade.stop_loss),
        "take_profit": _serialize_decimal(trade.take_profit),
        "opened_at": _serialize_datetime(trade.opened_at),
        "closed_at": _serialize_datetime(trade.closed_at),
        "pnl": _serialize_decimal(trade.pnl),
        "net_pnl": _serialize_decimal(trade.net_pnl),
        "commission": _serialize_decimal(trade.commission),
        "currency": trade.currency,
        "journal": trade.journal,
        "user_rating": trade.user_rating,
        "tradingview_link": trade.tradingview_link,
        "playbook_id": str(trade.playbook_id) if trade.playbook_id else None,
        "taxonomy_assignments": [
            {"taxonomy_id": str(item.taxonomy_id), "name": item.taxonomy.name if item.taxonomy else None} for item in trade.taxonomy_assignments
        ],
        "annotation_assignments": [
            {
                "annotation_definition_id": str(item.annotation_definition_id),
                "name": (item.annotation_definition.name if item.annotation_definition else None),
                "value": _annotation_typed_value(item.value_int, item.value_float, item.value_bool, item.value_string),
            }
            for item in trade.annotation_assignments
        ],
        "image_count": len(trade.image_urls),
        "image_filenames": [_filename_from_storage_ref(ref) for ref in trade.image_urls],
        "quick_notes": [
            {
                "id": str(note.id),
                "content": note.content,
                "emotion": note.emotion,
                "created_at": _serialize_datetime(note.created_at),
            }
            for note in notes
        ],
    }


async def _handle_get_checkin(
    user_id: uuid.UUID,
    db: AsyncSession,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    params = GetCheckinParams.model_validate(arguments)

    result = await db.execute(
        select(DailyCheckin)
        .where(DailyCheckin.user_id == user_id, DailyCheckin.id == params.checkin_id)
        .options(
            selectinload(DailyCheckin.taxonomy_assignments).selectinload(CheckinTaxonomy.taxonomy),
            selectinload(DailyCheckin.annotation_assignments).selectinload(CheckinAnnotation.annotation_definition),
        ),
    )
    checkin = result.scalar_one_or_none()
    if checkin is None:
        raise ValueError(f"Checkin {params.checkin_id} not found")

    return {
        "id": str(checkin.id),
        "date": checkin.date.isoformat(),
        "market_phase": checkin.market_phase,
        "notes": checkin.notes,
        "news_links": list(checkin.news_links or []),
        "custom_metrics": checkin.custom_metrics,
        "screenshot_count": len(checkin.screenshot_urls or []),
        "taxonomy_assignments": [
            {"taxonomy_id": str(item.taxonomy_id), "name": item.taxonomy.name if item.taxonomy else None} for item in checkin.taxonomy_assignments
        ],
        "annotation_assignments": [
            {
                "annotation_definition_id": str(item.annotation_definition_id),
                "name": (item.annotation_definition.name if item.annotation_definition else None),
                "value": _annotation_typed_value(item.value_int, item.value_float, item.value_bool, item.value_string),
            }
            for item in checkin.annotation_assignments
        ],
    }


async def _handle_get_taxonomy(
    user_id: uuid.UUID,
    db: AsyncSession,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    params = GetTaxonomyParams.model_validate(arguments)
    service = TaxonomyService(db)

    try:
        taxonomy = await service.get(user_id=user_id, taxonomy_id=params.taxonomy_id)
    except TaxonomyNotFoundError as exc:
        raise ValueError(str(exc)) from exc

    return {
        "id": str(taxonomy.id),
        "name": taxonomy.name,
        "scope": taxonomy.scope,
        "color_hex": taxonomy.color_hex,
        "description": taxonomy.description,
        "icon_identifier": taxonomy.icon_identifier,
        "is_archived": taxonomy.is_archived,
    }


async def _handle_get_annotation_definition(
    user_id: uuid.UUID,
    db: AsyncSession,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    params = GetAnnotationDefinitionParams.model_validate(arguments)
    service = AnnotationDefinitionService(db)

    try:
        definition = await service.get(user_id=user_id, definition_id=params.annotation_definition_id)
    except AnnotationDefinitionNotFoundError as exc:
        raise ValueError(str(exc)) from exc

    return {
        "id": str(definition.id),
        "name": definition.name,
        "type": definition.type,
        "scope": definition.scope,
        "scale_labels": definition.scale_labels,
        "description": definition.description,
        "icon_identifier": definition.icon_identifier,
        "is_archived": definition.is_archived,
    }


async def _handle_add_trade_note(
    user_id: uuid.UUID,
    db: AsyncSession,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    params = AddTradeNoteParams.model_validate(arguments)

    owned = await db.execute(
        select(Trade.id).where(Trade.user_id == user_id, Trade.id == params.trade_id),
    )
    if owned.scalar_one_or_none() is None:
        raise ValueError(f"Trade {params.trade_id} not found")

    note_service = NoteService(db)
    note = await note_service.add_note(
        trade_id=params.trade_id,
        data=TradeNoteCreate(content=params.content, emotion=params.emotion),
        user_id=user_id,
    )
    await db.flush()

    AuditEventService().create_audit_event(
        action="trade.note_added",
        user_id=user_id,
        email=None,
        resource_type="trade_note",
        resource_id=note.id,
        ip_address=None,
        user_agent="mcp",
        request_id=generate_request_id(),
        status_code=200,
        method="POST",
        path="/mcp/messages",
        metadata={"user_id": str(user_id), "trade_id": str(params.trade_id), "note_id": str(note.id)},
    )

    return {"note_id": str(note.id), "created_at": _serialize_datetime(note.created_at)}


async def _handle_update_trade_note(
    user_id: uuid.UUID,
    db: AsyncSession,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    params = UpdateTradeNoteParams.model_validate(arguments)

    update_data: dict[str, Any] = {}
    if params.content is not None:
        update_data["content"] = params.content
    if params.emotion is not None:
        update_data["emotion"] = params.emotion

    note_service = NoteService(db)
    try:
        note = await note_service.update_note(
            note_id=params.note_id,
            trade_id=params.trade_id,
            data=TradeNoteUpdate(**update_data),
            user_id=user_id,
        )
    except NoteNotFoundError as exc:
        raise ValueError(str(exc)) from exc
    await db.flush()

    AuditEventService().create_audit_event(
        action="trade.note_updated",
        user_id=user_id,
        email=None,
        resource_type="trade_note",
        resource_id=note.id,
        ip_address=None,
        user_agent="mcp",
        request_id=generate_request_id(),
        status_code=200,
        method="POST",
        path="/mcp/messages",
        metadata={"user_id": str(user_id), "trade_id": str(params.trade_id), "note_id": str(note.id)},
    )

    return {"note_id": str(note.id), "updated_at": _serialize_datetime(note.updated_at)}


async def _handle_delete_trade_note(
    user_id: uuid.UUID,
    db: AsyncSession,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    params = DeleteTradeNoteParams.model_validate(arguments)

    note_service = NoteService(db)
    try:
        await note_service.delete_note(note_id=params.note_id, trade_id=params.trade_id, user_id=user_id)
    except NoteNotFoundError as exc:
        raise ValueError(str(exc)) from exc
    await db.flush()

    AuditEventService().create_audit_event(
        action="trade.note_deleted",
        user_id=user_id,
        email=None,
        resource_type="trade_note",
        resource_id=params.note_id,
        ip_address=None,
        user_agent="mcp",
        request_id=generate_request_id(),
        status_code=200,
        method="POST",
        path="/mcp/messages",
        metadata={"user_id": str(user_id), "trade_id": str(params.trade_id), "note_id": str(params.note_id)},
    )

    return {"deleted": True}


async def _handle_update_trade_journal(
    user_id: uuid.UUID,
    db: AsyncSession,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    params = UpdateTradeJournalParams.model_validate(arguments)

    result = await db.execute(
        select(Trade).where(Trade.user_id == user_id, Trade.id == params.trade_id),
    )
    trade = result.scalar_one_or_none()
    if trade is None:
        raise ValueError(f"Trade {params.trade_id} not found")

    new_journal = f"{trade.journal}\n{params.text}" if params.mode == "append" and trade.journal else params.text

    trade_service = TradeService(db)
    try:
        await trade_service.update_trade(
            trade_id=params.trade_id,
            data=TradeUpdate(journal=new_journal),
            user_id=user_id,
        )
    except TradeNotFoundError as exc:
        raise ValueError(str(exc)) from exc

    AuditEventService().create_audit_event(
        action="trade.journal_updated",
        user_id=user_id,
        email=None,
        resource_type="trade",
        resource_id=params.trade_id,
        ip_address=None,
        user_agent="mcp",
        request_id=generate_request_id(),
        status_code=200,
        method="POST",
        path="/mcp/messages",
        metadata={"user_id": str(user_id), "trade_id": str(params.trade_id)},
    )

    return {"trade_id": str(params.trade_id)}


async def _handle_get_trade_attachments(
    user_id: uuid.UUID,
    db: AsyncSession,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    params = GetTradeAttachmentsParams.model_validate(arguments)

    result = await db.execute(
        select(Trade.image_urls).where(Trade.user_id == user_id, Trade.id == params.trade_id),
    )
    row = result.first()
    if row is None:
        raise ValueError(f"Trade {params.trade_id} not found")
    image_refs: list[str] = list(row[0] or [])

    max_items = params.max_items
    truncated = len(image_refs) > max_items
    selected_refs = image_refs[:max_items]

    storage_service = StorageService()
    content_blocks: list[dict[str, Any]] = []

    for ref in selected_refs:
        filename = _filename_from_storage_ref(ref)

        if params.format == "url":
            url = storage_service.generate_presigned_get_url(ref, settings.storage_presigned_get_ttl_seconds)
            content_blocks.append(_build_text_content_block(json.dumps({"filename": filename, "url": url})))
            continue

        try:
            data, content_type = storage_service.download_file_by_storage_ref(ref)
        except Exception:
            logger.exception("Failed to download trade attachment", extra={"storage_ref": ref})
            url = storage_service.generate_presigned_get_url(ref, settings.storage_presigned_get_ttl_seconds)
            content_blocks.append(
                _build_text_content_block(json.dumps({"filename": filename, "url": url, "error": "download_failed"})),
            )
            continue

        if len(data) > MCP_ATTACHMENT_MAX_INLINE_BYTES:
            url = storage_service.generate_presigned_get_url(ref, settings.storage_presigned_get_ttl_seconds)
            content_blocks.append(
                _build_text_content_block(
                    json.dumps({"filename": filename, "url": url, "note": "oversized_fallback_to_url"}),
                ),
            )
            continue

        content_blocks.append(_build_image_content_block(data, content_type))

    summary = _build_text_content_block(
        json.dumps(
            {
                "trade_id": str(params.trade_id),
                "format": params.format,
                "total_available": len(image_refs),
                "returned": len(selected_refs),
                "truncated": truncated,
            },
        ),
    )

    return {"_mcp_content": [summary, *content_blocks]}


async def _handle_get_playbook_attachments(
    user_id: uuid.UUID,
    db: AsyncSession,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    params = GetPlaybookAttachmentsParams.model_validate(arguments)

    result = await db.execute(
        select(Playbook)
        .where(Playbook.user_id == user_id, Playbook.id == params.playbook_id)
        .options(selectinload(Playbook.attachments), selectinload(Playbook.links)),
    )
    playbook = result.scalar_one_or_none()
    if playbook is None:
        raise ValueError(f"Playbook {params.playbook_id} not found")

    attachments = list(playbook.attachments)
    max_items = params.max_items
    truncated = len(attachments) > max_items
    selected = attachments[:max_items]

    storage_service = StorageService()
    content_blocks: list[dict[str, Any]] = []

    for attachment in selected:
        if params.format == "url":
            url = storage_service.generate_presigned_get_url(
                attachment.storage_url,
                settings.storage_presigned_get_ttl_playbook_seconds,
            )
            content_blocks.append(_build_text_content_block(json.dumps({"filename": attachment.filename, "url": url})))
            continue

        try:
            data, _content_type = storage_service.download_file_by_storage_ref(attachment.storage_url)
        except Exception:
            logger.exception("Failed to download playbook attachment", extra={"storage_ref": attachment.storage_url})
            url = storage_service.generate_presigned_get_url(
                attachment.storage_url,
                settings.storage_presigned_get_ttl_playbook_seconds,
            )
            content_blocks.append(
                _build_text_content_block(
                    json.dumps({"filename": attachment.filename, "url": url, "error": "download_failed"}),
                ),
            )
            continue

        if len(data) > MCP_ATTACHMENT_MAX_INLINE_BYTES:
            url = storage_service.generate_presigned_get_url(
                attachment.storage_url,
                settings.storage_presigned_get_ttl_playbook_seconds,
            )
            content_blocks.append(
                _build_text_content_block(
                    json.dumps({"filename": attachment.filename, "url": url, "note": "oversized_fallback_to_url"}),
                ),
            )
            continue

        content_blocks.append(_build_image_content_block(data, attachment.content_type))

    links_block = _build_text_content_block(
        json.dumps([{"label": link.label, "url": link.url} for link in playbook.links]),
    )

    summary = _build_text_content_block(
        json.dumps(
            {
                "playbook_id": str(params.playbook_id),
                "format": params.format,
                "total_available": len(attachments),
                "returned": len(selected),
                "truncated": truncated,
            },
        ),
    )

    return {"_mcp_content": [summary, *content_blocks, links_block]}


async def _handle_link_trade_playbook(
    user_id: uuid.UUID,
    db: AsyncSession,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    params = LinkTradePlaybookParams.model_validate(arguments)

    result = await db.execute(
        select(Trade).where(Trade.user_id == user_id, Trade.id == params.trade_id),
    )
    trade = result.scalar_one_or_none()
    if trade is None:
        raise ValueError(f"Trade {params.trade_id} not found")

    new_playbook_id: uuid.UUID | None
    if params.clear:
        new_playbook_id = None
    else:
        owned_playbook = await db.execute(
            select(Playbook.id).where(Playbook.user_id == user_id, Playbook.id == params.playbook_id),
        )
        if owned_playbook.scalar_one_or_none() is None:
            raise ValueError(f"Playbook {params.playbook_id} not found")
        new_playbook_id = params.playbook_id

    trade.playbook_id = new_playbook_id
    await db.flush()

    AuditEventService().create_audit_event(
        action="trade.playbook_linked",
        user_id=user_id,
        email=None,
        resource_type="trade",
        resource_id=trade.id,
        ip_address=None,
        user_agent="mcp",
        request_id=generate_request_id(),
        status_code=200,
        method="POST",
        path="/mcp/messages",
        metadata={
            "user_id": str(user_id),
            "trade_id": str(trade.id),
            "playbook_id": str(new_playbook_id) if new_playbook_id else None,
        },
    )

    return {
        "trade_id": str(trade.id),
        "playbook_id": str(new_playbook_id) if new_playbook_id else None,
    }


_TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    "get_metadata_schema": {
        "description": "Return active taxonomies and annotation definitions for the authenticated user.",
        "inputSchema": {"type": "object", "properties": {}},
        "handler": _handle_get_metadata_schema,
        "mutating": False,
    },
    "list_portfolios": {
        "description": "List all portfolios for the authenticated user. Returns id, name, and base currency.",
        "inputSchema": {"type": "object", "properties": {}},
        "handler": _handle_list_portfolios,
        "mutating": False,
    },
    "list_accounts": {
        "description": "List non-archived accounts for the authenticated user. Optionally filter by portfolio_id or broker (manual, schwab, ibkr).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "portfolio_id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "Filter accounts by portfolio UUID",
                },
                "broker": {
                    "type": "string",
                    "enum": ["manual", "schwab", "ibkr"],
                    "description": "Filter accounts by broker type",
                },
            },
        },
        "handler": _handle_list_accounts,
        "mutating": False,
    },
    "create_taxonomy": {
        "description": "Create a taxonomy definition with name, scope, color, and optional metadata.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "minLength": 1, "maxLength": 100},
                "scope": {"type": "string"},
                "color_hex": {"type": "string", "pattern": "^#[0-9A-Fa-f]{6}$"},
                "description": {"type": "string", "maxLength": 500},
                "icon_identifier": {"type": "string", "maxLength": 100},
            },
            "required": ["name", "scope", "color_hex"],
        },
        "handler": _handle_create_taxonomy,
        "mutating": True,
    },
    "update_taxonomy": {
        "description": "Update taxonomy metadata and optionally archive or unarchive it.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "taxonomy_id": {"type": "string", "format": "uuid"},
                "name": {"type": "string", "minLength": 1, "maxLength": 100},
                "scope": {"type": "string"},
                "color_hex": {"type": "string", "pattern": "^#[0-9A-Fa-f]{6}$"},
                "description": {"type": "string", "maxLength": 500},
                "icon_identifier": {"type": "string", "maxLength": 100},
                "is_archived": {"type": "boolean"},
            },
            "required": ["taxonomy_id"],
        },
        "handler": _handle_update_taxonomy,
        "mutating": True,
    },
    "delete_taxonomy": {
        "description": "Archive a taxonomy definition when it has no active assignments.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "taxonomy_id": {"type": "string", "format": "uuid"},
            },
            "required": ["taxonomy_id"],
        },
        "handler": _handle_delete_taxonomy,
        "mutating": True,
    },
    "create_annotation_definition": {
        "description": "Create an annotation definition with type, scope, and optional metadata.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "minLength": 1, "maxLength": 100},
                "type": {
                    "type": "string",
                    "enum": ["int", "float", "bool", "string_enum"],
                },
                "scope": {"type": "string"},
                "description": {"type": "string", "maxLength": 500},
                "icon_identifier": {"type": "string", "maxLength": 100},
                "scale_labels": {"type": "object"},
            },
            "required": ["name", "type", "scope"],
        },
        "handler": _handle_create_annotation_definition,
        "mutating": True,
    },
    "update_annotation_definition": {
        "description": "Update annotation definition metadata and optionally archive or unarchive it.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "annotation_definition_id": {"type": "string", "format": "uuid"},
                "name": {"type": "string", "minLength": 1, "maxLength": 100},
                "type": {
                    "type": "string",
                    "enum": ["int", "float", "bool", "string_enum"],
                },
                "scope": {"type": "string"},
                "description": {"type": "string", "maxLength": 500},
                "icon_identifier": {"type": "string", "maxLength": 100},
                "scale_labels": {"type": "object"},
                "is_archived": {"type": "boolean"},
            },
            "required": ["annotation_definition_id"],
        },
        "handler": _handle_update_annotation_definition,
        "mutating": True,
    },
    "delete_annotation_definition": {
        "description": "Archive an annotation definition when it has no active assignments.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "annotation_definition_id": {"type": "string", "format": "uuid"},
            },
            "required": ["annotation_definition_id"],
        },
        "handler": _handle_delete_annotation_definition,
        "mutating": True,
    },
    "list_checkins": {
        "description": "List check-ins with optional date range, taxonomy, and annotation filters. Returns taxonomy and annotation assignments per check-in.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "date_from": {"type": "string", "format": "date"},
                "date_to": {"type": "string", "format": "date"},
                "taxonomy_ids": {
                    "type": "array",
                    "items": {"type": "string", "format": "uuid"},
                    "description": "Filter by taxonomy UUIDs (AND logic: check-in must have all listed tags)",
                },
                "annotation_filters": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "annotation_definition_id": {"type": "string", "format": "uuid"},
                            "operator": {"type": "string", "enum": ["eq", "neq", "lt", "lte", "gt", "gte"]},
                            "value": {"oneOf": [{"type": "integer"}, {"type": "number"}, {"type": "boolean"}, {"type": "string"}]},
                            "logic": {"type": "string", "enum": ["and", "or"], "default": "and"},
                        },
                        "required": ["annotation_definition_id", "operator", "value"],
                    },
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": 200, "default": 50},
                "offset": {"type": "integer", "minimum": 0, "default": 0},
            },
        },
        "handler": _handle_list_checkins,
        "mutating": False,
    },
    "sync_checkin_metadata": {
        "description": "Bulk assign taxonomy tags and annotation values to a list of check-ins (upsert).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "checkin_ids": {
                    "type": "array",
                    "maxItems": 50,
                    "items": {"type": "string", "format": "uuid"},
                },
                "taxonomy_ids": {
                    "type": "array",
                    "items": {"type": "string", "format": "uuid"},
                },
                "annotations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "annotation_definition_id": {"type": "string", "format": "uuid"},
                            "value": {"oneOf": [{"type": "integer"}, {"type": "number"}, {"type": "boolean"}, {"type": "string"}]},
                        },
                        "required": ["annotation_definition_id", "value"],
                    },
                },
            },
            "required": ["checkin_ids"],
        },
        "handler": _handle_sync_checkin_metadata,
        "mutating": True,
    },
    "search_trades_advanced": {
        "description": "Search user trades with date, symbol, metadata, and portfolio filters.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "date_from": {"type": "string", "format": "date-time"},
                "date_to": {"type": "string", "format": "date-time"},
                "symbol": {"type": "string"},
                "asset_class": {
                    "type": "string",
                    "enum": ["EQUITY", "OPTION", "FUTURE", "FOREX", "CRYPTO"],
                },
                "pnl_min": {"type": "number"},
                "pnl_max": {"type": "number"},
                "taxonomy_ids": {
                    "type": "array",
                    "items": {"type": "string", "format": "uuid"},
                },
                "annotation_filters": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "annotation_definition_id": {
                                "type": "string",
                                "format": "uuid",
                            },
                            "operator": {
                                "type": "string",
                                "enum": ["eq", "neq", "lt", "gt", "lte", "gte"],
                            },
                            "value": {
                                "oneOf": [
                                    {"type": "integer"},
                                    {"type": "number"},
                                    {"type": "boolean"},
                                    {"type": "string"},
                                ]
                            },
                            "logic": {
                                "type": "string",
                                "enum": ["and", "or"],
                                "default": "and",
                            },
                        },
                        "required": ["annotation_definition_id", "operator", "value"],
                    },
                },
                "portfolio_id": {"type": "string", "format": "uuid"},
                "sort_by": {"type": "string", "enum": ["opened_at", "closed_at", "pnl", "net_pnl"], "default": "opened_at"},
                "sort_dir": {"type": "string", "enum": ["asc", "desc"], "default": "desc"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 200, "default": 50},
                "offset": {"type": "integer", "minimum": 0, "default": 0},
            },
        },
        "handler": _handle_search_trades_advanced,
        "mutating": False,
    },
    "sync_trade_metadata": {
        "description": "Bulk set journal text, taxonomy tags, and annotation values on trades (merges with existing assignments).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "trade_ids": {
                    "type": "array",
                    "maxItems": 50,
                    "items": {"type": "string", "format": "uuid"},
                },
                "journal": {"type": "string"},
                "taxonomy_ids": {
                    "type": "array",
                    "items": {"type": "string", "format": "uuid"},
                },
                "annotations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "annotation_definition_id": {
                                "type": "string",
                                "format": "uuid",
                            },
                            "value": {
                                "oneOf": [
                                    {"type": "integer"},
                                    {"type": "number"},
                                    {"type": "boolean"},
                                    {"type": "string"},
                                ]
                            },
                        },
                        "required": ["annotation_definition_id", "value"],
                    },
                },
            },
            "required": ["trade_ids"],
        },
        "handler": _handle_sync_trade_metadata,
        "mutating": True,
    },
    "sync_playbook_metadata": {
        "description": "Bulk assign taxonomy tags to a playbook (additive, idempotent; does not remove existing assignments).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "playbook_id": {"type": "string", "format": "uuid"},
                "taxonomy_ids": {
                    "type": "array",
                    "items": {"type": "string", "format": "uuid"},
                },
            },
            "required": ["playbook_id", "taxonomy_ids"],
        },
        "handler": _handle_sync_playbook_metadata,
        "mutating": True,
    },
    "list_strategy_playbooks": {
        "description": "List all strategy playbooks including assigned taxonomy tags.",
        "inputSchema": {"type": "object", "properties": {}},
        "handler": _handle_list_strategy_playbooks,
        "mutating": False,
    },
    "get_strategy_playbook": {
        "description": "Get detailed information about a specific strategy playbook including markdown description and assigned taxonomy tags.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "playbook_id": {"type": "string", "format": "uuid"},
            },
            "required": ["playbook_id"],
        },
        "handler": _handle_get_strategy_playbook,
        "mutating": False,
    },
    "create_strategy_playbook": {
        "description": "Create an active playbook with optional markdown description.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "maxLength": 100},
                "description": {"type": "string"},
                "target_winrate": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["name"],
        },
        "handler": _handle_create_strategy_playbook,
        "mutating": True,
    },
    "update_strategy_playbook": {
        "description": "Update an existing playbook's metadata and optionally assign taxonomy tags additively.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "playbook_id": {"type": "string", "format": "uuid"},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "taxonomy_ids": {
                    "type": "array",
                    "items": {"type": "string", "format": "uuid"},
                },
                "target_winrate": {"type": "number"},
                "is_active": {"type": "boolean"},
            },
            "required": ["playbook_id"],
        },
        "handler": _handle_update_strategy_playbook,
        "mutating": True,
    },
    "get_trade": {
        "description": (
            "Load a single trade by ID, including core fields, journal, taxonomy/annotation "
            "assignments, image reference count and filenames, and embedded quick notes."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "trade_id": {"type": "string", "format": "uuid"},
            },
            "required": ["trade_id"],
        },
        "handler": _handle_get_trade,
        "mutating": False,
    },
    "get_checkin": {
        "description": (
            "Load a single daily check-in by ID, including notes, market phase, custom metrics, "
            "news links, screenshot count, and full taxonomy/annotation assignment detail."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "checkin_id": {"type": "string", "format": "uuid"},
            },
            "required": ["checkin_id"],
        },
        "handler": _handle_get_checkin,
        "mutating": False,
    },
    "get_taxonomy": {
        "description": "Load a single taxonomy definition by ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "taxonomy_id": {"type": "string", "format": "uuid"},
            },
            "required": ["taxonomy_id"],
        },
        "handler": _handle_get_taxonomy,
        "mutating": False,
    },
    "get_annotation_definition": {
        "description": "Load a single annotation definition by ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "annotation_definition_id": {"type": "string", "format": "uuid"},
            },
            "required": ["annotation_definition_id"],
        },
        "handler": _handle_get_annotation_definition,
        "mutating": False,
    },
    "add_trade_note": {
        "description": "Append a new timestamped quick note (with optional emotion label) to an owned trade.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "trade_id": {"type": "string", "format": "uuid"},
                "content": {"type": "string", "minLength": 1, "maxLength": NOTE_MAX_LENGTH},
                "emotion": {"type": "string", "maxLength": EMOTION_MAX_LENGTH},
            },
            "required": ["trade_id", "content"],
        },
        "handler": _handle_add_trade_note,
        "mutating": True,
    },
    "update_trade_note": {
        "description": "Edit an existing quick note's content and/or emotion label.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "trade_id": {"type": "string", "format": "uuid"},
                "note_id": {"type": "string", "format": "uuid"},
                "content": {"type": "string", "minLength": 1, "maxLength": NOTE_MAX_LENGTH},
                "emotion": {"type": "string", "maxLength": EMOTION_MAX_LENGTH},
            },
            "required": ["trade_id", "note_id"],
        },
        "handler": _handle_update_trade_note,
        "mutating": True,
    },
    "delete_trade_note": {
        "description": "Delete an existing quick note from an owned trade.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "trade_id": {"type": "string", "format": "uuid"},
                "note_id": {"type": "string", "format": "uuid"},
            },
            "required": ["trade_id", "note_id"],
        },
        "handler": _handle_delete_trade_note,
        "mutating": True,
    },
    "update_trade_journal": {
        "description": "Set (replace) or append to the main journal notes field of a single owned trade.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "trade_id": {"type": "string", "format": "uuid"},
                "text": {"type": "string", "maxLength": JOURNAL_MAX_LENGTH},
                "mode": {"type": "string", "enum": ["replace", "append"], "default": "replace"},
            },
            "required": ["trade_id", "text"],
        },
        "handler": _handle_update_trade_journal,
        "mutating": True,
    },
    "get_trade_attachments": {
        "description": (
            "Return a trade's image attachments as base64 MCP image content blocks (default) or presigned URLs, bounded by max_items and a per-image byte cap."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "trade_id": {"type": "string", "format": "uuid"},
                "format": {"type": "string", "enum": ["image", "url"], "default": "image"},
                "max_items": {"type": "integer", "minimum": 1, "maximum": MCP_ATTACHMENT_MAX_ITEMS, "default": MCP_ATTACHMENT_MAX_ITEMS},
            },
            "required": ["trade_id"],
        },
        "handler": _handle_get_trade_attachments,
        "mutating": False,
    },
    "get_playbook_attachments": {
        "description": (
            "Return a playbook's image attachments (base64 blocks or presigned URLs) and labeled links, bounded by max_items and a per-image byte cap."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "playbook_id": {"type": "string", "format": "uuid"},
                "format": {"type": "string", "enum": ["image", "url"], "default": "image"},
                "max_items": {"type": "integer", "minimum": 1, "maximum": MCP_ATTACHMENT_MAX_ITEMS, "default": MCP_ATTACHMENT_MAX_ITEMS},
            },
            "required": ["playbook_id"],
        },
        "handler": _handle_get_playbook_attachments,
        "mutating": False,
    },
    "link_trade_playbook": {
        "description": "Set or clear the linked playbook of an owned trade. Pass playbook_id to set (must also be owned), or clear:true to remove the link.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "trade_id": {"type": "string", "format": "uuid"},
                "playbook_id": {"type": "string", "format": "uuid"},
                "clear": {"type": "boolean", "default": False},
            },
            "required": ["trade_id"],
        },
        "handler": _handle_link_trade_playbook,
        "mutating": True,
    },
}


def _sse_event_stream(
    request: Request,
    session_id: str | None,
    user_id: str,
) -> StreamingResponse:
    if session_id and not re.match(r"^[A-Za-z0-9_-]{1,64}$", session_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session_id format.",
        )

    # In MCP SSE, the server controls the session_id if not provided
    if not session_id:
        session_id = str(uuid.uuid4())

    message_endpoint = f"/mcp/messages?session_id={session_id}"

    # Create a message queue for this session
    queue: asyncio.Queue[str] = asyncio.Queue()
    _ACTIVE_STREAMS[session_id] = (uuid.UUID(user_id), queue)

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }

    async def event_generator() -> AsyncGenerator[str, None]:
        # Contract decision: keep the legacy-compatible `ready` SSE event with a
        # JSON payload containing both `session_id` and `endpoint`.
        # Some clients key off `ready`, others need the endpoint URL for
        # follow-up POSTs to /mcp/messages.
        ready_payload = json.dumps({"session_id": session_id, "endpoint": message_endpoint})
        yield f"event: ready\ndata: {ready_payload}\n\n"

        if request.headers.get("x-test-no-sse-keepalive") == "true":
            _ACTIVE_STREAMS.pop(session_id, None)
            return

        try:
            while True:
                try:
                    # Wait for a message or send a keepalive
                    msg = await asyncio.wait_for(queue.get(), timeout=_KEEPALIVE_INTERVAL)
                    yield f"event: message\ndata: {msg}\n\n"
                except TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            # Cleanup when the connection drops
            _ACTIVE_STREAMS.pop(session_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=headers,
    )


async def _dispatch_jsonrpc(
    payload: dict[str, Any],
    user_id: uuid.UUID,
    db: AsyncSession,
) -> dict[str, Any]:
    """Shared JSON-RPC dispatch logic for both legacy and Streamable HTTP transports."""
    if payload.get("jsonrpc") != "2.0":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="jsonrpc must be '2.0'.",
        )

    message_id = payload.get("id")
    method = payload.get("method")
    if not isinstance(method, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="method is required.",
        )

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": message_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "Trade Sensei MCP", "version": "1.0"},
                "capabilities": {"tools": {}},
            },
        }

    if method == "ping":
        return {
            "jsonrpc": "2.0",
            "id": message_id,
            "result": {"pong": True, "user_id": str(user_id)},
        }

    if method == "notifications/initialized":
        # Client acknowledgement — no response needed (notification has no id)
        return {}

    if method == "tools/list":
        tools = [
            {
                "name": name,
                "description": tool["description"],
                "inputSchema": tool["inputSchema"],
            }
            for name, tool in _TOOL_REGISTRY.items()
        ]
        return {
            "jsonrpc": "2.0",
            "id": message_id,
            "result": {"tools": tools},
        }

    if method == "tools/call":
        params = payload.get("params")
        if not isinstance(params, dict):
            return {
                "jsonrpc": "2.0",
                "id": message_id,
                "error": _tool_error(-32602, "params must be an object"),
            }

        tool_name = params.get("name")
        if not isinstance(tool_name, str):
            return {
                "jsonrpc": "2.0",
                "id": message_id,
                "error": _tool_error(-32602, "Tool name is required"),
            }

        arguments = params.get("arguments", {})
        if not isinstance(arguments, dict):
            return {
                "jsonrpc": "2.0",
                "id": message_id,
                "error": _tool_error(-32602, "arguments must be an object"),
            }

        tool = _TOOL_REGISTRY.get(tool_name)
        if tool is None:
            return {
                "jsonrpc": "2.0",
                "id": message_id,
                "error": _tool_error(-32601, f"Unknown tool: {tool_name}"),
            }

        try:
            raw_result: dict[str, Any] = await tool["handler"](
                user_id=user_id,
                db=db,
                arguments=arguments,
            )
            # MCP spec requires tools/call result to have a "content" array.
            # Handlers may opt into returning non-text blocks (e.g. images) by
            # returning {"_mcp_content": [...]}; those blocks are used verbatim.
            # All other handlers keep the existing single-text-block wrapping.
            if "_mcp_content" in raw_result:
                mcp_result = {"content": raw_result["_mcp_content"]}
            else:
                mcp_result = {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(raw_result),
                        }
                    ]
                }
            return {
                "jsonrpc": "2.0",
                "id": message_id,
                "result": mcp_result,
            }
        except (ValidationError, ValueError) as exc:
            return {
                "jsonrpc": "2.0",
                "id": message_id,
                "error": _tool_error(-32602, str(exc)),
            }
        except Exception:
            logger.exception("MCP tool execution failed", extra={"tool": tool_name})
            return {
                "jsonrpc": "2.0",
                "id": message_id,
                "error": _tool_error(-32603, "Internal error"),
            }

    return {
        "jsonrpc": "2.0",
        "id": message_id,
        "error": {"code": -32601, "message": f"Unknown method: {method}"},
    }


# ── Streamable HTTP transport (MCP spec 2024-11-05 / 2025-03-26) ──────────────
# MCP Inspector and modern clients use POST /mcp with Accept: application/json
# or Accept: text/event-stream.  A single endpoint handles both.


@router.post(
    "",
    summary="MCP Streamable HTTP transport",
    response_model=None,
    responses={401: {"description": "Missing or invalid PAT."}},
)
async def mcp_streamable(
    request: Request,
    mcp_context: Annotated[tuple[User, AsyncSession], Depends(_get_mcp_session_with_rls)],
) -> JSONResponse | StreamingResponse:
    """Handle MCP Streamable HTTP transport (POST /mcp).

    Accepts a JSON-RPC 2.0 payload and returns either:
    - A plain JSON response when ``Accept`` prefers ``application/json``.
    - An SSE stream wrapping the response when ``Accept`` includes
      ``text/event-stream`` (used by some MCP clients).
    """
    try:
        payload: dict[str, Any] = await request.json()
    except Exception:
        return JSONResponse(
            {"jsonrpc": "2.0", "id": None, "error": _tool_error(-32700, "Parse error")},
            status_code=400,
        )

    current_user, db = mcp_context

    result = await _dispatch_jsonrpc(
        payload=payload,
        user_id=current_user.id,
        db=db,
    )

    # Notification (no id) — respond with 202 No Content
    if not result:
        return JSONResponse(content=None, status_code=202)

    accept = request.headers.get("accept", "application/json")

    if "text/event-stream" in accept:
        # Wrap the single response in an SSE stream so streaming-aware clients work
        response_json = json.dumps(result)

        async def _single_event() -> AsyncGenerator[str, None]:
            yield f"event: message\ndata: {response_json}\n\n"

        return StreamingResponse(
            _single_event(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    return JSONResponse(content=result)


@router.get(
    "/sse",
    summary="Initialize MCP SSE transport (legacy)",
    responses={401: {"description": "Missing or invalid PAT."}},
)
async def mcp_sse(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user_from_pat)],
    session_id: str | None = Query(default=None, description="MCP session identifier"),
) -> StreamingResponse:
    return _sse_event_stream(
        request=request,
        session_id=session_id,
        user_id=str(current_user.id),
    )


@router.post(
    "/messages",
    summary="Process MCP JSON-RPC message (legacy SSE transport)",
    responses={401: {"description": "Missing or invalid PAT."}},
)
async def mcp_messages(
    payload: dict[str, Any],
    mcp_context: Annotated[tuple[User, AsyncSession], Depends(_get_mcp_session_with_rls)],
    session_id: str | None = Query(default=None, description="MCP session identifier"),
) -> Response:
    if not session_id or session_id not in _ACTIVE_STREAMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or missing session_id. The SSE stream must be opened first.",
        )

    current_user, db = mcp_context

    stream_owner, queue = _ACTIVE_STREAMS[session_id]
    if stream_owner != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session belongs to a different user.",
        )

    result = await _dispatch_jsonrpc(
        payload=payload,
        user_id=current_user.id,
        db=db,
    )

    if result:
        # Route the JSON-RPC response back over the active SSE stream
        await queue.put(json.dumps(result))

    return Response(status_code=status.HTTP_202_ACCEPTED)
