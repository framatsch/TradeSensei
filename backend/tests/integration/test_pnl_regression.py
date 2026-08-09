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

from decimal import Decimal
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select

from app.models.broker_raw_transaction import BrokerRawTransaction
from app.models.corporate_action import CorporateAction
from app.models.logical_execution import LogicalExecution
from app.models.trade import Trade
from app.services.import_service import ImportService
from app.utils.parsers.factory import BrokerType
from tests.test_import_ground_truth import _create_account, _register_and_login

pytestmark = pytest.mark.asyncio


@pytest.mark.integration
async def test_sequential_import_matches_in_memory_ground_truth(
    client: AsyncClient, db_session
):
    """
    This test is the ultimate Source of Truth for the FIFO Aggregator.

    It validates that importing broker files sequentially into the database
    produces the EXACT same Net P&L as the all-at-once in-memory ground truth.

    This explicitly tests two deeply complex edge cases:
    1. Cross-year open lots with splits: OTLK had a reverse split in 2024.
       The 2023 seed lots must be adjusted by the 2024 corporate action correctly
       before matching against the 2024 closing executions.
    2. Cross-year options/multiplier: VST or other options opened in one year
       and closed in another must keep their `multiplier` (e.g., 100) so they
       are correctly calculated upon exit.

    If this test fails, a refactoring has broken the aggregation logic.
    Do NOT change the expected outcomes in this test; change the code to pass it.
    """

    # 1. Setup paths to the test XML files.
    # Prefer split historical files; fall back to the anonymized combined fixture.
    base_dir = Path(__file__).resolve().parent.parent.parent
    split_paths = [
        base_dir / "TraderJournal_2023.xml",
        base_dir / "TraderJournal_2024.xml",
        base_dir / "TraderJournal_2025.xml",
        base_dir / "TraderJournal_Q1_2026.xml",
    ]
    if all(p.exists() for p in split_paths):
        paths = split_paths
    else:
        paths = [
            base_dir.parent
            / "tests"
            / "test_data"
            / "ibkr"
            / "TraderJournal_anonymized_combined.xml"
        ]

    # If no fixture is available, skip safely.
    if not all(p.exists() for p in paths):
        pytest.skip("Historical XML fixtures not found. Skipping full regression test.")

    # Calculate the IN-MEMORY Ground Truth trades directly
    from tests.integration.ground_truth_aggregator import (
        _parse_raw_files,
        _stable_sort_executions,
        aggregate_executions_fifo,
        logical_executions_to_trade_creates,
    )

    raw_records, corporate_actions = _parse_raw_files(paths)
    sorted_raw_records = _stable_sort_executions(raw_records)
    execution_trades = logical_executions_to_trade_creates(sorted_raw_records)
    gt_trades = aggregate_executions_fifo(
        execution_trades, corporate_actions=corporate_actions
    )

    expected_total_pnl = sum(
        (
            (t.net_pnl if getattr(t, "net_pnl", None) is not None else t.pnl)
            for t in gt_trades
            if getattr(t, "closed_at", None) is not None
            and getattr(t, "pnl", None) is not None
        ),
        Decimal("0"),
    )

    # 3. Clean DB state for safety
    await db_session.execute(delete(Trade))
    await db_session.execute(delete(CorporateAction))
    await db_session.execute(delete(LogicalExecution))
    await db_session.execute(delete(BrokerRawTransaction))
    await db_session.commit()

    token, user_id = await _register_and_login(client)
    portfolio_id, account_id = await _create_account(client, token)

    # 4. Sequentially import into the DB
    service = ImportService(db_session)
    for p in paths:
        await service.import_file(
            content=p.read_bytes(),
            filename=p.name,
            broker=BrokerType.IBKR,
            portfolio_id=portfolio_id,
            account_id=account_id,
            user_id=user_id,
        )
        # Service flushes, but we need to commit to persist for the next loop iteration's queries
        await db_session.commit()

    # 5. Fetch resulting DB Trades
    result = await db_session.execute(select(Trade).where(Trade.pnl.is_not(None)))
    trades = result.scalars().all()

    # Calculate DB Total Net PnL (fallback to gross PnL if net is null, which shouldn't be the case here)
    db_total_pnl = sum(
        (
            (t.net_pnl if t.net_pnl is not None else t.pnl)
            for t in trades
            if t.pnl is not None
        ),
        Decimal("0"),
    )

    db_symbols = {}
    for t in trades:
        y = t.closed_at.year
        if y not in db_symbols:
            db_symbols[y] = {}
        if t.symbol not in db_symbols[y]:
            db_symbols[y][t.symbol] = {"pnl": Decimal("0"), "count": 0}
        val = t.net_pnl if t.net_pnl is not None else t.pnl
        if val is not None:
            db_symbols[y][t.symbol]["pnl"] += val
        db_symbols[y][t.symbol]["count"] += 1

    gt_symbols = {}
    for t in gt_trades:
        if getattr(t, "closed_at", None) is None:
            continue
        y = t.closed_at.year
        if y not in gt_symbols:
            gt_symbols[y] = {}
        if t.symbol not in gt_symbols[y]:
            gt_symbols[y][t.symbol] = {"pnl": Decimal("0"), "count": 0}
        val = t.net_pnl if getattr(t, "net_pnl", None) is not None else t.pnl
        if val is not None:
            gt_symbols[y][t.symbol]["pnl"] += val
        gt_symbols[y][t.symbol]["count"] += 1

    for y in sorted(set(db_symbols.keys()) | set(gt_symbols.keys())):
        print(f"\\nYear {y}:")
        all_syms = sorted(
            set(db_symbols.get(y, {}).keys()) | set(gt_symbols.get(y, {}).keys())
        )
        for sym in all_syms:
            db_stats = db_symbols.get(y, {}).get(sym, {"pnl": Decimal("0"), "count": 0})
            gt_stats = gt_symbols.get(y, {}).get(sym, {"pnl": Decimal("0"), "count": 0})

            if (
                abs(db_stats["pnl"] - gt_stats["pnl"]) > Decimal("0.01")
                or db_stats["count"] != gt_stats["count"]
            ):
                print(
                    f"  MISMATCH {sym}: DB={db_stats['count']} trades, {db_stats['pnl']} PnL | GT={gt_stats['count']} trades, {gt_stats['pnl']} PnL"
                )

    assert abs(db_total_pnl - expected_total_pnl) < Decimal("0.01")

    # Calculate OTLK PnL specifically to ensure the 2024 Reverse Split (ratio 0.05)
    # was correctly applied to the 2023 seed lots.
    db_otlk_pnl = sum(
        (t.net_pnl for t in trades if t.symbol == "OTLK" and t.net_pnl is not None),
        Decimal("0"),
    )

    # The expected value is derived from the in-memory GT aggregator for OTLK.
    # Do NOT hard-code; compute from the same ground-truth pass used above.
    expected_otlk_pnl = sum(
        (
            (t.net_pnl if getattr(t, "net_pnl", None) is not None else t.pnl)
            for t in gt_trades
            if t.symbol == "OTLK"
            and getattr(t, "closed_at", None) is not None
            and getattr(t, "pnl", None) is not None
        ),
        Decimal("0"),
    )

    assert abs(db_otlk_pnl - expected_otlk_pnl) < Decimal("0.01"), (
        f"CRITICAL: OTLK Cross-Year Corporate Action (Split) failed. "
        f"Expected {expected_otlk_pnl}, got {db_otlk_pnl}."
    )
