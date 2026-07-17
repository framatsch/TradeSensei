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

"""Extended unit tests for ImportService — targeting uncovered branches."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AccountNotFoundError
from app.utils.parsers.factory import BrokerType

pytestmark = pytest.mark.asyncio

_USER_ID = uuid.uuid4()
_PORTFOLIO_ID = uuid.uuid4()
_ACCOUNT_ID = uuid.uuid4()


# ---------------------------------------------------------------------------
# Helper factory
# ---------------------------------------------------------------------------


def _make_service():
    from app.services.import_service import ImportService

    svc = ImportService.__new__(ImportService)
    svc._session = AsyncMock()
    svc._account_repo = AsyncMock()
    svc._trade_repo = AsyncMock()
    svc._ca_repo = AsyncMock()
    svc._portfolio_repo = AsyncMock()
    svc._raw_repo = AsyncMock()
    svc._logical_svc = AsyncMock()
    svc._exec_repo = AsyncMock()
    svc._audit = MagicMock()
    return svc


def _make_mock_account():
    a = MagicMock()
    a.id = _ACCOUNT_ID
    a.account_number = "ACC-123"
    return a


def _make_mock_portfolio(base_currency: str = "USD"):
    p = MagicMock()
    p.id = _PORTFOLIO_ID
    p.base_currency = base_currency
    return p


def _make_mock_trade_create(
    symbol: str = "AAPL",
    currency: str = "USD",
    db_trade_id: uuid.UUID | None = None,
    broker_conid: str = "12345",
    direction: str = "LONG",
):
    from app.models.trade import Direction as TradeDirection

    t = MagicMock()
    t.symbol = symbol
    t.currency = currency
    t.opened_at = datetime(2024, 1, 15, 9, 30)
    t.closed_at = None
    t.entry_price = Decimal("100")
    t.exit_price = None
    t.quantity = Decimal("10")
    t.pnl = None
    t.broker_conid = broker_conid
    t.db_trade_id = db_trade_id
    t.direction = TradeDirection.LONG
    t.is_combo = False
    t.model_copy = MagicMock(return_value=t)
    return t


# ---------------------------------------------------------------------------
# import_file - account not found
# ---------------------------------------------------------------------------


async def test_import_file_raises_when_account_not_found():
    svc = _make_service()
    svc._account_repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(AccountNotFoundError):
        await svc.import_file(
            content=b"data",
            filename="file.csv",
            broker=BrokerType.IBKR,
            portfolio_id=_PORTFOLIO_ID,
            account_id=_ACCOUNT_ID,
            user_id=_USER_ID,
        )


async def test_import_file_adds_currency_mismatch_warning():
    svc = _make_service()
    svc._account_repo.get_by_id = AsyncMock(return_value=None)  # no account
    svc._portfolio_repo.get_by_id = AsyncMock(return_value=_make_mock_portfolio(base_currency="USD"))
    svc._ca_repo.list_by_user = AsyncMock(return_value=[])
    svc._trade_repo.list_open_lots_by_user = AsyncMock(return_value=[])
    svc._trade_repo.list_orphaned_lots_by_user = AsyncMock(return_value=[])
    svc._trade_repo.list_manually_edited_keys = AsyncMock(return_value=set())
    svc._trade_repo.list_existing_entry_keys = AsyncMock(return_value=set())
    svc._trade_repo.list_existing_close_keys = AsyncMock(return_value=set())

    trade = _make_mock_trade_create(currency="EUR")  # EUR != USD

    mock_parser = MagicMock()
    mock_parser.parse_raw = MagicMock(side_effect=NotImplementedError)
    mock_parser.parse = MagicMock(return_value=([trade], []))
    mock_parser.warnings = []
    mock_parser.enrich_pnl_eur = AsyncMock()

    with patch("app.services.import_service.get_parser", return_value=mock_parser):
        result = await svc.import_file(
            content=b"data",
            filename="file.csv",
            broker=BrokerType.IBKR,
            portfolio_id=_PORTFOLIO_ID,
            account_id=None,
            user_id=_USER_ID,
        )

    assert any("currency_mismatch" in w for w in result.warnings)


async def test_import_file_no_account_id_skips_account_lookup():
    svc = _make_service()
    svc._portfolio_repo.get_by_id = AsyncMock(return_value=_make_mock_portfolio())
    svc._ca_repo.list_by_user = AsyncMock(return_value=[])
    svc._trade_repo.list_open_lots_by_user = AsyncMock(return_value=[])
    svc._trade_repo.list_orphaned_lots_by_user = AsyncMock(return_value=[])
    svc._trade_repo.list_manually_edited_keys = AsyncMock(return_value=set())
    svc._trade_repo.list_existing_entry_keys = AsyncMock(return_value=set())
    svc._trade_repo.list_existing_close_keys = AsyncMock(return_value=set())

    mock_parser = MagicMock()
    mock_parser.parse_raw = MagicMock(side_effect=NotImplementedError)
    mock_parser.parse = MagicMock(return_value=([], []))
    mock_parser.warnings = []
    mock_parser.enrich_pnl_eur = AsyncMock()

    with patch("app.services.import_service.get_parser", return_value=mock_parser):
        result = await svc.import_file(
            content=b"data",
            filename="file.csv",
            broker=BrokerType.IBKR,
            portfolio_id=_PORTFOLIO_ID,
            account_id=None,
            user_id=_USER_ID,
        )

    svc._account_repo.get_by_id.assert_not_called()
    assert result.trades_created == 0


async def test_import_file_skips_manually_edited_trades():
    svc = _make_service()
    svc._portfolio_repo.get_by_id = AsyncMock(return_value=_make_mock_portfolio())
    svc._ca_repo.list_by_user = AsyncMock(return_value=[])
    svc._trade_repo.list_open_lots_by_user = AsyncMock(return_value=[])
    svc._trade_repo.list_orphaned_lots_by_user = AsyncMock(return_value=[])

    trade = _make_mock_trade_create()
    match_key = (trade.broker_conid, trade.opened_at)
    svc._trade_repo.list_manually_edited_keys = AsyncMock(return_value={match_key})
    svc._trade_repo.list_existing_entry_keys = AsyncMock(return_value=set())
    svc._trade_repo.list_existing_close_keys = AsyncMock(return_value=set())

    mock_parser = MagicMock()
    mock_parser.parse_raw = MagicMock(side_effect=NotImplementedError)
    mock_parser.parse = MagicMock(return_value=([trade], []))
    mock_parser.warnings = []
    mock_parser.enrich_pnl_eur = AsyncMock()

    with patch("app.services.import_service.get_parser", return_value=mock_parser):
        result = await svc.import_file(
            content=b"data",
            filename="file.csv",
            broker=BrokerType.IBKR,
            portfolio_id=_PORTFOLIO_ID,
            account_id=None,
            user_id=_USER_ID,
        )

    assert result.trades_created == 0


# ---------------------------------------------------------------------------
# set_statement_timeout
# ---------------------------------------------------------------------------


async def test_set_statement_timeout_sets_when_positive():
    svc = _make_service()
    svc._session.execute = AsyncMock()

    await svc.set_statement_timeout(30)

    svc._session.execute.assert_called_once()


async def test_set_statement_timeout_skips_when_zero():
    svc = _make_service()
    svc._session.execute = AsyncMock()

    await svc.set_statement_timeout(0)

    svc._session.execute.assert_not_called()

# ---------------------------------------------------------------------------
# _split_execution_for_trade
# ---------------------------------------------------------------------------

from app.core.exceptions import TradeNotFoundError, ExecutionNotFoundError

async def test_split_execution_raises_when_trade_not_found():
    svc = _make_service()
    svc._trade_repo.get_by_id = AsyncMock(return_value=None)
    with pytest.raises(TradeNotFoundError):
        await svc._split_execution_for_trade(uuid.uuid4(), Decimal("5"), uuid.uuid4(), _USER_ID)

async def test_split_execution_raises_when_execution_not_found():
    svc = _make_service()
    svc._trade_repo.get_by_id = AsyncMock(return_value=MagicMock())
    svc._exec_repo.get_by_id = AsyncMock(return_value=None)
    with pytest.raises(ExecutionNotFoundError):
        await svc._split_execution_for_trade(uuid.uuid4(), Decimal("5"), uuid.uuid4(), _USER_ID)

async def test_split_execution_success():
    svc = _make_service()
    svc._trade_repo.get_by_id = AsyncMock(return_value=MagicMock())
    orig_exec = MagicMock()
    orig_exec.id = uuid.uuid4()
    orig_exec.user_id = _USER_ID
    orig_exec.account_id = _ACCOUNT_ID
    orig_exec.symbol = "AAPL"
    orig_exec.conid = "12345"
    orig_exec.asset_class = "STK"
    orig_exec.direction = "LONG"
    orig_exec.quantity = Decimal("10")
    orig_exec.price = Decimal("100")
    orig_exec.commission = Decimal("2")
    orig_exec.executed_at = datetime.now(timezone.utc)
    orig_exec.pnl = Decimal("50")
    orig_exec.currency = "USD"
    orig_exec.multiplier = 1
    
    svc._exec_repo.get_by_id = AsyncMock(return_value=orig_exec)
    svc._exec_repo.soft_delete = AsyncMock()
    
    child = MagicMock()
    svc._exec_repo.create = AsyncMock(return_value=child)
    
    result = await svc._split_execution_for_trade(orig_exec.id, Decimal("5"), uuid.uuid4(), _USER_ID)
    
    assert result == child
    svc._exec_repo.soft_delete.assert_called_once_with(orig_exec.id)
    assert svc._exec_repo.create.call_count == 2  # one for trade, one for remainder

# ---------------------------------------------------------------------------
# _process_execution_split
# ---------------------------------------------------------------------------

async def test_process_execution_split_no_changes():
    svc = _make_service()
    orig_exec = MagicMock()
    orig_exec.user_id = _USER_ID
    orig_exec.quantity = Decimal("10")
    orig_exec.commission = Decimal("2")
    await svc._process_execution_split(orig_exec, [], _USER_ID)
    svc._exec_repo.soft_delete_many.assert_not_called()

async def test_process_execution_split_with_changes():
    from app.utils.parsers.aggregator import ExecutionAllocation
    svc = _make_service()
    
    orig_exec = MagicMock()
    orig_exec.id = uuid.uuid4()
    orig_exec.user_id = _USER_ID
    orig_exec.account_id = _ACCOUNT_ID
    orig_exec.symbol = "AAPL"
    orig_exec.quantity = Decimal("10")
    orig_exec.price = Decimal("100")
    orig_exec.commission = Decimal("2")
    orig_exec.executed_at = datetime.now()
    
    svc._exec_repo.get_by_id = AsyncMock(return_value=orig_exec)
    svc._exec_repo.soft_delete_many = AsyncMock()
    svc._exec_repo.create_many = AsyncMock(return_value=[])
    
    alloc = ExecutionAllocation(
        execution_id=orig_exec.id,
        quantity_used=Decimal("5"),
        commission_used=Decimal("1"),
        entry_price=Decimal("100"),
    )
    
    trade_id = uuid.uuid4()
    await svc._process_execution_split(orig_exec, [(trade_id, alloc)], _USER_ID)
    
    svc._exec_repo.soft_delete.assert_called_once()
    svc._exec_repo.create.assert_called()

