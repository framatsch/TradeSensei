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

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.trade import Trade
from app.services.import_service import ImportService
from app.utils.parsers.aggregator import (
    ExecutionLike,
    aggregate_executions_fifo,
    logical_executions_to_trade_creates,
)
from app.utils.parsers.factory import BrokerType
from app.utils.parsers.ibkr_xml import IBKRXMLParser
from tests.test_import_ground_truth import _create_account, _register_and_login

pytestmark = pytest.mark.asyncio

_FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "ibkr"
_OPEN_XML = _FIXTURES_DIR / "seed_open_year1.xml"
_CLOSE_XML = _FIXTURES_DIR / "seed_close_year2.xml"


def _q(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.00000001"))


@pytest.mark.integration
async def test_cross_import_seed_lot_regression(client: AsyncClient, db_session) -> None:
    parser = IBKRXMLParser()
    raw1, ca1 = parser.parse_raw(_OPEN_XML.read_bytes(), _OPEN_XML.name)
    assert parser.warnings == [], f"seed_open_year1.xml warnings: {parser.warnings}"

    raw2, ca2 = parser.parse_raw(_CLOSE_XML.read_bytes(), _CLOSE_XML.name)
    assert parser.warnings == [], f"seed_close_year2.xml warnings: {parser.warnings}"

    all_raw = sorted(raw1 + raw2, key=lambda row: (row.executed_at, row.id))
    all_ca = ca1 + ca2
    gt_trades = aggregate_executions_fifo(
        logical_executions_to_trade_creates(cast(list[ExecutionLike], all_raw)),
        corporate_actions=all_ca,
    )

    token, user_id = await _register_and_login(client)
    portfolio_id, account_id = await _create_account(client, token)

    service = ImportService(db_session)
    for path in (_OPEN_XML, _CLOSE_XML):
        await service.import_trades(
            content=path.read_bytes(),
            filename=path.name,
            broker=BrokerType.IBKR,
            portfolio_id=portfolio_id,
            account_id=account_id,
            user_id=user_id,
        )
        await db_session.commit()

    result = await db_session.execute(
        select(Trade).where(
            Trade.user_id == user_id,
            Trade.account_id == account_id,
            Trade.symbol.in_(["SEEDA", "SPLT"]),
        )
    )
    trades = list(result.scalars().all())

    closed = [trade for trade in trades if trade.closed_at is not None]
    open_lots = [trade for trade in trades if trade.closed_at is None]
    assert len(closed) == 2
    assert len(open_lots) == 0

    seeda = next(trade for trade in closed if trade.symbol == "SEEDA")
    assert seeda.opened_at.year == 2024
    assert seeda.closed_at is not None and seeda.closed_at.year == 2025
    assert seeda.quantity == Decimal("100")
    assert seeda.entry_price == Decimal("10")
    assert seeda.exit_price == Decimal("11")

    splt = next(trade for trade in closed if trade.symbol == "SPLT")
    assert splt.opened_at.year == 2024
    assert splt.closed_at is not None and splt.closed_at.year == 2025
    assert splt.quantity == Decimal("10")
    assert splt.entry_price == Decimal("100")
    assert splt.exit_price == Decimal("80")
    assert splt.pnl == Decimal("-200")

    db_by_year: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    for trade in closed:
        year = trade.closed_at.year
        value = trade.net_pnl if trade.net_pnl is not None else trade.pnl
        if value is not None:
            db_by_year[year] += _q(value)

    gt_by_year: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    for trade in gt_trades:
        if trade.closed_at is None:
            continue
        value = trade.net_pnl if trade.net_pnl is not None else trade.pnl
        if value is not None:
            gt_by_year[trade.closed_at.year] += _q(value)

    assert set(db_by_year.keys()) == set(gt_by_year.keys())
    for year in sorted(gt_by_year):
        assert abs(db_by_year[year] - gt_by_year[year]) < Decimal("0.01")
