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

"""Integration tests for BrokerRawTransactionRepository helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.broker_raw_transaction import BrokerRawTransaction
from app.models.trade import AssetClass, Direction
from app.models.user import User
from app.repositories.broker_raw_transaction_repository import (
    BrokerRawTransactionRepository,
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_combo_order_meta_by_raw_ids_returns_empty_for_empty_input(
    db_session: AsyncSession,
) -> None:
    repo = BrokerRawTransactionRepository(db_session)
    result = await repo.get_combo_order_meta_by_raw_ids([])
    assert result == {}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_combo_order_meta_by_raw_ids_extracts_order_id_and_net_cash(
    db_session: AsyncSession,
) -> None:
    user = User(
        username=f"brt_repo_{uuid.uuid4().hex[:8]}",
        email=f"brt_repo_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="not-used",
    )
    db_session.add(user)
    await db_session.flush()

    row_a = BrokerRawTransaction(
        id=f"{user.id}:ibkr:1001",
        user_id=user.id,
        account_id=None,
        broker_type="ibkr",
        symbol="QQQ",
        conid="123",
        asset_class=AssetClass.OPTION,
        direction=Direction.LONG,
        quantity=Decimal("1"),
        price=Decimal("1.23"),
        commission=Decimal("0.65"),
        executed_at=datetime(2026, 1, 1, tzinfo=UTC),
        pnl=None,
        currency="USD",
        multiplier=100,
        open_close="O",
        raw_data={"brokerageOrderID": "combo-open-1", "netCash": "-123.45"},
        suppressed=False,
    )
    row_b = BrokerRawTransaction(
        id=f"{user.id}:ibkr:1002",
        user_id=user.id,
        account_id=None,
        broker_type="ibkr",
        symbol="QQQ",
        conid="456",
        asset_class=AssetClass.OPTION,
        direction=Direction.SHORT,
        quantity=Decimal("1"),
        price=Decimal("0.80"),
        commission=Decimal("0.65"),
        executed_at=datetime(2026, 1, 1, tzinfo=UTC),
        pnl=None,
        currency="USD",
        multiplier=100,
        open_close="O",
        raw_data={"brokerageOrderID": "combo-open-1", "netCash": "80.00"},
        suppressed=False,
    )
    db_session.add_all([row_a, row_b])
    await db_session.flush()

    repo = BrokerRawTransactionRepository(db_session)
    result = await repo.get_combo_order_meta_by_raw_ids([row_a.id, row_b.id, "missing-id"])

    assert set(result.keys()) == {row_a.id, row_b.id}
    assert result[row_a.id]["brokerageOrderID"] == "combo-open-1"
    assert result[row_b.id]["brokerageOrderID"] == "combo-open-1"
    assert result[row_a.id]["netCash"] == Decimal("-123.45")
    assert result[row_b.id]["netCash"] == Decimal("80.00")
