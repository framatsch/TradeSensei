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

"""Normalized, deterministic snapshots of the persisted import state.

Used by the import golden-master suite to prove that a refactor does not
change observable import behavior. Every value is reduced to a stable JSON
form:

- rows are sorted by content-derived keys, never by database IDs;
- UUIDs are replaced by ordinal references (``T0``, ``E3`` …) that are
  assigned in that stable sort order; ``position_id`` is reduced to its
  presence (its grouping is not deterministic, see ``capture_import_state``);
- timestamps are ISO-8601 in UTC, Decimals are strings;
- the test user/account IDs embedded in strings (e.g. raw transaction IDs)
  are replaced by ``<user>`` / ``<account>``;
- Python set literals inside messages are sorted (their order depends on the
  interpreter hash seed).

Columns are serialized generically from the ORM table definition, so a new
column automatically shows up in the snapshot diff.
"""

from __future__ import annotations

import enum
import hashlib
import json
import re
import uuid
from collections.abc import Iterable, Mapping
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.broker_raw_transaction import BrokerRawTransaction
from app.models.corporate_action import CorporateAction
from app.models.logical_execution import LogicalExecution
from app.models.playbook import Playbook
from app.models.taxonomy import Taxonomy
from app.models.trade import Trade
from app.models.trade_note import TradeNote
from app.models.trade_taxonomy import TradeTaxonomy

_UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
_VOLATILE_COLUMNS = frozenset({"created_at", "updated_at"})
# Python ``set`` reprs embedded in messages (e.g. combo warnings) have
# hash-seed dependent element order; their elements are sorted.
_SET_LITERAL_RE = re.compile(r"\{'[^'{}]*'(?:, '[^'{}]*')*\}")


def _sort_set_literal(match: re.Match[str]) -> str:
    elements = sorted(match.group(0)[1:-1].split(", "))
    return "{" + ", ".join(elements) + "}"


class _Normalizer:
    """Replace test-run specific identifiers with stable placeholders."""

    def __init__(self, user_id: uuid.UUID, account_id: uuid.UUID | None) -> None:
        self._replacements: list[tuple[str, str]] = [(str(user_id), "<user>")]
        if account_id is not None:
            self._replacements.append((str(account_id), "<account>"))

    def text(self, value: str) -> str:
        for needle, placeholder in self._replacements:
            value = value.replace(needle, placeholder)
        value = _SET_LITERAL_RE.sub(_sort_set_literal, value)
        return _UUID_RE.sub("<uuid>", value)

    def value(self, value: Any) -> Any:
        if value is None or isinstance(value, bool | int):
            return value
        if isinstance(value, str):
            return self.text(value)
        if isinstance(value, enum.Enum):
            return self.value(value.value)
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, float):
            return repr(value)
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return f"NAIVE:{value.isoformat()}"
            return value.astimezone(UTC).isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, uuid.UUID):
            return self.text(str(value))
        if isinstance(value, Mapping):
            return {str(k): self.value(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
        if isinstance(value, list | tuple):
            return [self.value(v) for v in value]
        if isinstance(value, BaseModel):
            return self.value(value.model_dump(mode="python"))
        raise TypeError(f"Unsupported snapshot value type: {type(value)!r}")


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _columns(row: Any, exclude: Iterable[str]) -> list[str]:
    excluded = set(exclude) | _VOLATILE_COLUMNS
    return [column.name for column in row.__table__.columns if column.name not in excluded]


def _plain_fields(row: Any, normalizer: _Normalizer, exclude: Iterable[str]) -> dict[str, Any]:
    return {name: normalizer.value(getattr(row, name)) for name in _columns(row, exclude)}


def normalize_import_result(result: BaseModel | Mapping[str, Any], user_id: uuid.UUID, account_id: uuid.UUID | None) -> Any:
    """Return a normalized JSON-compatible form of an import/sync result or response body."""
    return _Normalizer(user_id, account_id).value(result)


def normalize_error(exc: BaseException, user_id: uuid.UUID, account_id: uuid.UUID | None) -> dict[str, str]:
    """Return a normalized description of an expected import error."""
    return {"type": type(exc).__name__, "message": _Normalizer(user_id, account_id).text(str(exc))}


async def capture_import_state(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
) -> dict[str, Any]:
    """Capture the normalized persisted import state for one user/account.

    Args:
        session: Session used to read the state (expired first so values are
            re-read from the database).
        user_id: Owning test user.
        account_id: Target account of the imports.

    Returns:
        A JSON-compatible dict with raw transactions, logical executions,
        trades (incl. metadata), corporate actions and the account number.
    """
    session.expire_all()
    norm = _Normalizer(user_id, account_id)

    raws = list((await session.execute(select(BrokerRawTransaction).where(BrokerRawTransaction.user_id == user_id))).scalars().all())
    executions = list((await session.execute(select(LogicalExecution).where(LogicalExecution.user_id == user_id))).scalars().all())
    trades = list((await session.execute(select(Trade).where(Trade.user_id == user_id))).scalars().all())
    corporate_actions = list((await session.execute(select(CorporateAction).where(CorporateAction.user_id == user_id))).scalars().all())
    playbooks = {pb.id: pb.name for pb in (await session.execute(select(Playbook).where(Playbook.user_id == user_id))).scalars().all()}
    notes = list((await session.execute(select(TradeNote).where(TradeNote.user_id == user_id))).scalars().all())
    tags = list(
        (
            await session.execute(
                select(TradeTaxonomy.trade_id, Taxonomy.name).join(Taxonomy, Taxonomy.id == TradeTaxonomy.taxonomy_id).where(Taxonomy.user_id == user_id)
            )
        ).all()
    )
    account = (await session.execute(select(Account).where(Account.id == account_id))).scalar_one()

    # ── Raw transactions ────────────────────────────────────────────────────
    raw_rows: list[dict[str, Any]] = []
    for raw in raws:
        fields = _plain_fields(raw, norm, exclude={"raw_data"})
        fields["raw_data_sha256"] = hashlib.sha256(_canonical(norm.value(raw.raw_data)).encode("utf-8")).hexdigest()
        raw_rows.append(fields)
    raw_rows.sort(key=_canonical)

    # ── Logical executions: content descriptors (no UUID references) ───────
    uuid_exec_columns = {"id", "trade_id", "parent_id"}
    exec_base = {e.id: _canonical(_plain_fields(e, norm, exclude=uuid_exec_columns)) for e in executions}
    exec_parent = {e.id: (exec_base.get(e.parent_id, "<missing-parent>") if e.parent_id else "") for e in executions}

    # ── Trades: content descriptors incl. their linked executions ───────────
    uuid_trade_columns = {"id", "position_id", "playbook_id"}
    execs_by_trade: dict[uuid.UUID, list[str]] = {}
    for e in executions:
        if e.trade_id is not None:
            execs_by_trade.setdefault(e.trade_id, []).append(exec_base[e.id] + "|" + exec_parent[e.id])
    notes_by_trade: dict[uuid.UUID, list[str]] = {}
    for note in notes:
        notes_by_trade.setdefault(note.trade_id, []).append(norm.text(note.content))
    tags_by_trade: dict[uuid.UUID, list[str]] = {}
    for trade_id, tag_name in tags:
        tags_by_trade.setdefault(trade_id, []).append(tag_name)

    trade_payload: dict[uuid.UUID, dict[str, Any]] = {}
    trade_key: dict[uuid.UUID, str] = {}
    for t in trades:
        fields = _plain_fields(t, norm, exclude=uuid_trade_columns)
        fields["playbook"] = playbooks.get(t.playbook_id, "<unknown-playbook>") if t.playbook_id else None
        fields["notes"] = sorted(notes_by_trade.get(t.id, []))
        fields["tags"] = sorted(tags_by_trade.get(t.id, []))
        trade_payload[t.id] = fields
        trade_key[t.id] = _canonical(fields) + "|" + _canonical(sorted(execs_by_trade.get(t.id, [])))

    sorted_trades = sorted(trades, key=lambda t: trade_key[t.id])
    trade_ref = {t.id: f"T{i}" for i, t in enumerate(sorted_trades)}

    def _exec_sort_key(e: LogicalExecution) -> tuple[str, str, str]:
        linked_trade_key = trade_key.get(e.trade_id, "<dangling>") if e.trade_id else ""
        return (exec_base[e.id], exec_parent[e.id], linked_trade_key)

    sorted_execs = sorted(executions, key=_exec_sort_key)
    exec_ref = {e.id: f"E{i}" for i, e in enumerate(sorted_execs)}

    exec_rows: list[dict[str, Any]] = []
    for e in sorted_execs:
        fields = json.loads(exec_base[e.id])
        fields["ref"] = exec_ref[e.id]
        fields["trade"] = trade_ref.get(e.trade_id, "<dangling>") if e.trade_id else None
        fields["parent"] = exec_ref.get(e.parent_id, "<missing-parent>") if e.parent_id else None
        exec_rows.append(fields)

    trade_rows: list[dict[str, Any]] = []
    for t in sorted_trades:
        fields = trade_payload[t.id]
        fields["ref"] = trade_ref[t.id]
        # Only presence is stable: ImportService._assign_position_ids_from_sources
        # picks the canonical position_id by iterating a set of random trade
        # UUIDs, so the grouping of overlapping split groups varies per run.
        fields["has_position"] = t.position_id is not None
        fields["legs"] = sorted(exec_ref[e.id] for e in executions if e.trade_id == t.id)
        trade_rows.append(fields)

    ca_rows = sorted(
        (_plain_fields(ca, norm, exclude={"id"}) for ca in corporate_actions),
        key=_canonical,
    )

    return {
        "account_number": account.account_number,
        "raw_transactions": raw_rows,
        "logical_executions": exec_rows,
        "trades": trade_rows,
        "corporate_actions": ca_rows,
    }


def dump_snapshot(snapshot: Any) -> str:
    """Serialize a snapshot to the committed on-disk JSON form."""
    return json.dumps(snapshot, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
