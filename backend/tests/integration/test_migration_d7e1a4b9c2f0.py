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

"""Migration d7e1a4b9c2f0: backfill of broker-neutral raw transaction fields.

Seeds ``broker_raw_transactions`` with the pre-migration schema from every
IBKR golden-master fixture plus hand-written edge rows, upgrades, and asserts
that the backfilled columns equal (a) the runtime extraction they replace —
the former JSONB query and ``LogicalExecutionService`` flip detection — and
(b) what the IBKR parser now writes for the same rows.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import sqlalchemy as sa
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncEngine

from alembic import command
from app.utils.parsers.ibkr_xml import IBKRXMLParser

_PREVIOUS_REVISION = "c4a8d2e9f301"
_REVISION = "d7e1a4b9c2f0"
_BACKEND_TESTS = Path(__file__).resolve().parents[1]
_FIXTURES = [
    *sorted((_BACKEND_TESTS / "fixtures" / "ibkr").glob("*.xml")),
    _BACKEND_TESTS.parents[1] / "tests" / "test_data" / "ibkr" / "combo_positions.xml",
    _BACKEND_TESTS.parents[1] / "tests" / "test_data" / "ibkr" / "TraderJournal_anonymized_combined.xml",
]

# raw_data payloads that never come out of the current parsers but may exist
# in historic rows; every one must be backfilled without failing the migration.
_EDGE_RAW_DATA: dict[str, dict[str, object]] = {
    "empty_order_and_cash": {"brokerageOrderID": "", "netCash": ""},
    "non_numeric_cash": {"brokerageOrderID": "o-1", "netCash": "n/a"},
    "padded_cash": {"netCash": " -12.5 "},
    "tab_padded_cash": {"netCash": "\t1.5\n"},
    "exponent_cash": {"netCash": "1.5E+2"},
    "lowercase_flip": {"openCloseIndicator": "c;o"},
    "reverse_flip": {"openCloseIndicator": "O;C"},
    "plain_close": {"openCloseIndicator": "C"},
    "json_null_values": {"brokerageOrderID": None, "netCash": None, "openCloseIndicator": None},
    "schwab_like": {"activityId": 1, "orderId": 2, "netAmount": -10},
    "no_keys": {},
}


def _old_is_mixed(raw_data: dict[str, Any]) -> bool:
    """Former LogicalExecutionService.create_from_raw flip detection."""
    indicator = str(raw_data.get("openCloseIndicator", "")).upper()
    return "C;O" in indicator or "O;C" in indicator


def _run_alembic(cfg: Config, cmd: str, revision: str) -> None:
    getattr(command, cmd)(cfg, revision)


@pytest.mark.integration
async def test_backfill_matches_runtime_extraction_and_parser(engine: AsyncEngine) -> None:
    cfg = Config("alembic.ini")
    await engine.dispose()
    await asyncio.to_thread(_run_alembic, cfg, "downgrade", _PREVIOUS_REVISION)

    user_id = uuid.uuid4()
    now = datetime.now(UTC)
    parser_expected: dict[str, tuple[str | None, Decimal | None, bool]] = {}
    rows: list[dict[str, Any]] = []
    for path in _FIXTURES:
        records, _ = IBKRXMLParser().parse_raw(path.read_bytes(), path.name)
        for record in records:
            row_id = f"{user_id}:{path.stem}:{record.id}"
            parser_expected[row_id] = (record.order_id, record.net_cash, record.is_mixed_execution)
            rows.append({"id": row_id, "symbol": record.symbol, "raw_data": record.raw_data})
    for name, raw_data in _EDGE_RAW_DATA.items():
        rows.append({"id": f"{user_id}:edge:{name}", "symbol": "EDGE", "raw_data": raw_data})

    try:
        async with engine.begin() as conn:
            await conn.execute(
                sa.text("INSERT INTO users (id, username, email, hashed_password, created_at, updated_at) VALUES (:id, :u, :e, 'x', :ts, :ts)"),
                {"id": user_id, "u": f"mig_{user_id.hex[:8]}", "e": f"mig_{user_id.hex[:8]}@example.com", "ts": now},
            )
            for row in rows:
                await conn.execute(
                    sa.text(
                        "INSERT INTO broker_raw_transactions "
                        "(id, user_id, broker_type, symbol, asset_class, direction, quantity, price, executed_at, raw_data) "
                        "VALUES (:id, :uid, 'ibkr', :symbol, 'EQUITY', 'LONG', 1, 1, :ts, CAST(:raw AS jsonb))"
                    ),
                    {"id": row["id"], "uid": user_id, "symbol": row["symbol"], "ts": now, "raw": json.dumps(row["raw_data"])},
                )

            # Runtime extraction before this change (BrokerRawTransactionRepository
            # .get_combo_order_meta_by_raw_ids). The numeric cast is evaluated only
            # where it succeeded before — a non-numeric netCash failed the import.
            old_meta = {
                r.id: (r.order_id, r.net_cash)
                for r in await conn.execute(
                    sa.text(
                        "SELECT id, raw_data->>'brokerageOrderID' AS order_id, "
                        "CASE WHEN id NOT IN (:bad1, :bad2) THEN CAST(raw_data->>'netCash' AS NUMERIC) END AS net_cash "
                        "FROM broker_raw_transactions WHERE user_id = :uid"
                    ),
                    {"uid": user_id, "bad1": f"{user_id}:edge:empty_order_and_cash", "bad2": f"{user_id}:edge:non_numeric_cash"},
                )
            }
            old_groups: dict[str, set[str]] = {}
            for row_id, (order_id, _) in old_meta.items():
                if order_id:
                    old_groups.setdefault(order_id, set()).add(row_id)

        await engine.dispose()
        await asyncio.to_thread(_run_alembic, cfg, "upgrade", _REVISION)

        async with engine.connect() as conn:
            migrated = {
                r.id: (r.order_id, r.net_cash, r.is_mixed_execution)
                for r in await conn.execute(
                    sa.text("SELECT id, order_id, net_cash, is_mixed_execution FROM broker_raw_transactions WHERE user_id = :uid"),
                    {"uid": user_id},
                )
            }

        raw_data_by_id = {row["id"]: row["raw_data"] for row in rows}
        assert set(migrated) == set(raw_data_by_id)
        for row_id, (order_id, net_cash, is_mixed) in migrated.items():
            old_order_id, old_net_cash = old_meta[row_id]
            assert order_id == old_order_id, row_id
            if old_net_cash is None:
                assert net_cash is None, row_id
            else:
                assert net_cash == old_net_cash, row_id
            assert is_mixed is _old_is_mixed(raw_data_by_id[row_id]), row_id

        # Combo grouping (non-empty order id → member rows) is identical.
        new_groups: dict[str, set[str]] = {}
        for row_id, (order_id, _, _) in migrated.items():
            if order_id:
                new_groups.setdefault(order_id, set()).add(row_id)
        assert new_groups == old_groups

        # Backfilled rows equal what the parser writes for new imports.
        for row_id, (order_id, net_cash, is_mixed) in parser_expected.items():
            assert migrated[row_id] == (order_id, net_cash, is_mixed), row_id

        # Edge rows: invalid / empty cash become NULL, empty order id stays "".
        edge = {name: migrated[f"{user_id}:edge:{name}"] for name in _EDGE_RAW_DATA}
        assert edge["empty_order_and_cash"] == ("", None, False)
        assert edge["non_numeric_cash"] == ("o-1", None, False)
        assert edge["padded_cash"][1] == Decimal("-12.5")
        assert edge["tab_padded_cash"][1] == Decimal("1.5")
        assert edge["exponent_cash"][1] == Decimal("150")
        assert edge["lowercase_flip"][2] is True
        assert edge["reverse_flip"][2] is True
        assert edge["json_null_values"] == (None, None, False)
        assert edge["schwab_like"] == (None, None, False)
    finally:
        await engine.dispose()
        await asyncio.to_thread(_run_alembic, cfg, "upgrade", "head")
        async with engine.begin() as conn:
            await conn.execute(sa.text("DELETE FROM users WHERE id = :id"), {"id": user_id})
