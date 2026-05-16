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

"""Regression tests for portfolio ownership hardening in repositories."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.account_repository import AccountRepository
from app.repositories.trade_repository import TradeRepository
from app.schemas.account import AccountSettings


@pytest.mark.unit
async def test_update_settings_scopes_update_by_user_id() -> None:
    session = AsyncMock()
    repo = AccountRepository(session)

    account_id = uuid.uuid4()
    user_id = uuid.uuid4()

    await repo.update_settings(
        account_id=account_id,
        user_id=user_id,
        settings=AccountSettings(sync_days=30),
    )

    stmt = session.execute.await_args.args[0]
    sql = str(stmt)
    assert "accounts.user_id" in sql
    assert "accounts.id" in sql


@pytest.mark.unit
async def test_upsert_property_non_owner_writes_nothing() -> None:
    session = AsyncMock()
    session.execute.return_value = MagicMock(scalar_one_or_none=lambda: None)
    repo = AccountRepository(session)

    await repo.upsert_property(
        account_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        key="SCHWAB_APP_KEY",
        encrypted_value="encrypted-value",
    )

    assert session.execute.await_count == 1


@pytest.mark.unit
async def test_close_open_lot_scopes_update_by_user_id() -> None:
    session = AsyncMock()
    repo = TradeRepository(session)

    await repo.close_open_lot(
        trade_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        exit_price=Decimal("11"),
        closed_at=datetime.now(UTC),
        pnl=Decimal("1"),
        pnl_eur=Decimal("1"),
        net_pnl=Decimal("1"),
        net_pnl_eur=Decimal("1"),
        commission_add=Decimal("0"),
        quantity=Decimal("1"),
    )

    stmt = session.execute.await_args.args[0]
    sql = str(stmt)
    assert "trades.user_id" in sql
    assert "trades.id" in sql


@pytest.mark.unit
async def test_fill_orphaned_lot_scopes_update_by_user_id() -> None:
    session = AsyncMock()
    repo = TradeRepository(session)

    await repo.fill_orphaned_lot(
        trade_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        entry_price=Decimal("10"),
        opened_at=datetime.now(UTC),
        pnl=Decimal("1"),
        pnl_eur=Decimal("1"),
        net_pnl=Decimal("1"),
        net_pnl_eur=Decimal("1"),
        commission_add=Decimal("0"),
        quantity=Decimal("1"),
    )

    stmt = session.execute.await_args.args[0]
    sql = str(stmt)
    assert "trades.user_id" in sql
    assert "trades.id" in sql
