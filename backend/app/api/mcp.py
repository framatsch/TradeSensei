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
import json
import logging
import re
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, ValidationError, model_validator
from sqlalchemy import and_, exists, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.database import get_session
from app.core.deps import get_current_user_from_pat
from app.models.account import Account, AccountType
from app.models.annotation_definition import AnnotationDefinition
from app.models.playbook import Playbook
from app.models.portfolio import Portfolio
from app.models.taxonomy import Taxonomy
from app.models.trade import AssetClass, Trade
from app.models.trade_annotation import TradeAnnotation
from app.models.trade_taxonomy import TradeTaxonomy
from app.models.user import User
from app.services.audit_service import AuditEventService, generate_request_id
from app.utils.annotation_mapping import map_value_to_column

router = APIRouter(prefix="/mcp", tags=["mcp"])
logger = logging.getLogger(__name__)

_KEEPALIVE_INTERVAL = 15

# Global dictionary to map session IDs to their event queues for SSE routing.
_ACTIVE_STREAMS: dict[str, asyncio.Queue[str]] = {}


class AnnotationFilter(BaseModel):
    annotation_definition_id: uuid.UUID
    operator: str
    value: int | float | bool | str


class AdvancedTradeSearchParams(BaseModel):
    date_from: datetime | None = None
    date_to: datetime | None = None
    symbol: str | None = Field(default=None, max_length=50)
    asset_class: AssetClass | None = None
    pnl_min: Decimal | None = None
    pnl_max: Decimal | None = None
    taxonomy_ids: list[uuid.UUID] = Field(default_factory=list)
    annotation_filters: list[AnnotationFilter] | None = None
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
    notes: str | None = None
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
    rules: list[str] = Field(min_length=1)
    target_winrate: float | None = Field(default=None, ge=0.0, le=1.0)


class UpdateStrategyPlaybookParams(BaseModel):
    playbook_id: uuid.UUID
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    rules: list[str] | None = None
    target_winrate: float | None = Field(default=None, ge=0.0, le=1.0)
    is_active: bool | None = None


class GetStrategyPlaybookParams(BaseModel):
    playbook_id: uuid.UUID


class ListAccountsParams(BaseModel):
    portfolio_id: uuid.UUID | None = None
    broker: str | None = Field(default=None, max_length=50)


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


def _annotation_value_column_and_value(
    operator: str,
    value: int | float | bool | str,
) -> tuple[Any, Any]:
    if isinstance(value, bool):
        if operator != "eq":
            raise ValueError("bool annotation filters support only 'eq' operator")
        return TradeAnnotation.value_bool, value

    if isinstance(value, int):
        return TradeAnnotation.value_int, value

    if isinstance(value, float):
        return TradeAnnotation.value_float, Decimal(str(value))

    if isinstance(value, str):
        if operator != "eq":
            raise ValueError("string annotation filters support only 'eq' operator")
        return TradeAnnotation.value_string, value

    raise ValueError("Unsupported annotation filter value type")


def _annotation_operator_expression(operator: str, column: Any, value: Any) -> Any:
    if operator == "eq":
        return column == value
    if operator == "lt":
        return column < value
    if operator == "gt":
        return column > value
    if operator == "lte":
        return column <= value
    if operator == "gte":
        return column >= value
    raise ValueError(f"Unsupported annotation filter operator: {operator}")


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
        for annotation_filter in params.annotation_filters:
            column, typed_value = _annotation_value_column_and_value(
                annotation_filter.operator,
                annotation_filter.value,
            )
            condition = _annotation_operator_expression(
                annotation_filter.operator,
                column,
                typed_value,
            )
            annotation_exists = exists(
                select(1)
                .select_from(TradeAnnotation)
                .join(
                    AnnotationDefinition,
                    TradeAnnotation.annotation_definition_id == AnnotationDefinition.id,
                )
                .where(
                    TradeAnnotation.trade_id == Trade.id,
                    AnnotationDefinition.user_id == user_id,
                    AnnotationDefinition.is_archived.is_(False),
                    TradeAnnotation.annotation_definition_id == annotation_filter.annotation_definition_id,
                    condition,
                ),
            )
            query = query.where(annotation_exists)

    if params.portfolio_id is not None:
        query = query.join(Account, Trade.account_id == Account.id).where(
            Account.portfolio_id == params.portfolio_id,
        )

    count_query = select(func.count()).select_from(query.with_only_columns(Trade.id).order_by(None).subquery())
    total_result = await db.execute(count_query)
    total = int(total_result.scalar_one())

    if params.sort_by == "pnl":
        sort_col = Trade.pnl
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

    if params.notes is not None:
        await db.execute(
            update(Trade).where(Trade.id.in_(owned_trade_ids)).values(notes=params.notes),
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

    rules_markdown = "\n".join(f"- {rule}" for rule in params.rules)
    playbook = Playbook(
        user_id=user_id,
        name=params.name,
        description=params.description,
        content_markdown=rules_markdown,
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
        playbook.name = params.name

    if params.description is not None:
        playbook.description = params.description
    
    if params.rules is not None:
        playbook.content_markdown = "\n".join(f"- {rule}" for rule in params.rules)
        
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

    return {
        "playbook_id": str(playbook.id), 
        "name": playbook.name,
        "is_active": playbook.is_active
    }


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
    return {
        "playbooks": [
            {
                "id": str(p.id),
                "name": p.name,
                "description": p.description,
                "target_winrate": _serialize_decimal(p.target_winrate),
                "is_active": p.is_active,
                "created_at": _serialize_datetime(p.created_at),
            }
            for p in playbooks
        ],
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
        
    return {
        "id": str(p.id),
        "name": p.name,
        "description": p.description,
        "content_markdown": p.content_markdown,
        "target_winrate": _serialize_decimal(p.target_winrate),
        "is_active": p.is_active,
        "created_at": _serialize_datetime(p.created_at),
        "updated_at": _serialize_datetime(p.updated_at),
    }


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
                                "enum": ["eq", "lt", "gt", "lte", "gte"],
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
                        "required": ["annotation_definition_id", "operator", "value"],
                    },
                },
                "portfolio_id": {"type": "string", "format": "uuid"},
                "sort_by": {
                    "type": "string", 
                    "enum": ["opened_at", "closed_at", "pnl", "net_pnl"], 
                    "default": "opened_at"
                },
                "sort_dir": {
                    "type": "string", 
                    "enum": ["asc", "desc"], 
                    "default": "desc"
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": 200, "default": 50},
                "offset": {"type": "integer", "minimum": 0, "default": 0},
            },
        },
        "handler": _handle_search_trades_advanced,
        "mutating": False,
    },
    "sync_trade_metadata": {
        "description": "Bulk add notes, taxonomy tags, and annotation values to trades (merges with existing assignments).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "trade_ids": {
                    "type": "array",
                    "maxItems": 50,
                    "items": {"type": "string", "format": "uuid"},
                },
                "notes": {"type": "string"},
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
    "list_strategy_playbooks": {
        "description": "List all strategy playbooks (including basic metadata).",
        "inputSchema": {"type": "object", "properties": {}},
        "handler": _handle_list_strategy_playbooks,
        "mutating": False,
    },
    "get_strategy_playbook": {
        "description": "Get detailed information about a specific strategy playbook including its rules in markdown format.",
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
        "description": "Create an active playbook from AI-supplied structured rules.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "maxLength": 100},
                "description": {"type": "string"},
                "rules": {"type": "array", "minItems": 1, "items": {"type": "string"}},
                "target_winrate": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["name", "rules"],
        },
        "handler": _handle_create_strategy_playbook,
        "mutating": True,
    },
    "update_strategy_playbook": {
        "description": "Update an existing playbook's metadata or rules.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "playbook_id": {"type": "string", "format": "uuid"},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "rules": {"type": "array", "items": {"type": "string"}},
                "target_winrate": {"type": "number"},
                "is_active": {"type": "boolean"},
            },
            "required": ["playbook_id"],
        },
        "handler": _handle_update_strategy_playbook,
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
    _ACTIVE_STREAMS[session_id] = queue

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }

    async def event_generator() -> AsyncGenerator[str, None]:
        # MCP spec requires an 'endpoint' event containing the URI as a string
        yield f"event: endpoint\ndata: {message_endpoint}\n\n"

        if request.headers.get("x-test-no-sse-keepalive") == "true":
            _ACTIVE_STREAMS.pop(session_id, None)
            return

        try:
            while True:
                try:
                    # Wait for a message or send a keepalive
                    msg = await asyncio.wait_for(queue.get(), timeout=_KEEPALIVE_INTERVAL)
                    yield f"event: message\ndata: {msg}\n\n"
                except asyncio.TimeoutError:
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
            # MCP spec requires tools/call result to have a "content" array
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
    current_user: Annotated[User, Depends(get_current_user_from_pat)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> JSONResponse | StreamingResponse:
    """Handle MCP Streamable HTTP transport (POST /mcp).

    Accepts a JSON-RPC 2.0 payload and returns either:
    - A plain JSON response when ``Accept`` prefers ``application/json``.
    - An SSE stream wrapping the response when ``Accept`` includes
      ``text/event-stream`` (used by some MCP clients).
    """
    try:
        payload: dict[str, Any] = await request.json()
        logger.error(f"MCP PAYLOAD RECEIVED: {json.dumps(payload)}")
    except Exception:
        return JSONResponse(
            {"jsonrpc": "2.0", "id": None, "error": _tool_error(-32700, "Parse error")},
            status_code=400,
        )

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
    current_user: Annotated[User, Depends(get_current_user_from_pat)],
    db: Annotated[AsyncSession, Depends(get_session)],
    session_id: str | None = Query(default=None, description="MCP session identifier"),
) -> Response:
    if not session_id or session_id not in _ACTIVE_STREAMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or missing session_id. The SSE stream must be opened first.",
        )

    result = await _dispatch_jsonrpc(
        payload=payload,
        user_id=current_user.id,
        db=db,
    )
    
    if result:
        # Route the JSON-RPC response back over the active SSE stream
        await _ACTIVE_STREAMS[session_id].put(json.dumps(result))
        
    return Response(status_code=status.HTTP_202_ACCEPTED)
