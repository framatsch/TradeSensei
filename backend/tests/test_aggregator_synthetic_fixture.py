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

"""FIFO aggregation correctness tests driven by synthetic IBKR XML fixtures.

These tests are the *ground-truth harness* for the FIFO pipeline.  They do NOT
depend on real broker data; all fixtures live in tests/fixtures/ibkr/ and are
fully anonymised, deterministic, and checked into version control.

Two fixtures cover six distinct aggregation scenarios:

``synthetic_year1.xml``  (IBKR Account U99999999, calendar year 2024)
  S1  Simple same-year round-trip          AAPL  BUY 10 @ 150 → SELL 10 @ 155
  S2  Partial close (two exits)            MSFT  BUY 20 @ 200 → SELL 10 @ 210, SELL 10 @ 220
  S3  Cross-year open (closed in year 2)   TSLA  BUY 5 @ 100
  S4  Pre-split open (10:1 RS in year 2)   SPLK  BUY 100 @ 10  conid=111
  S5  C;O position flip                    NFLX  BUY 10 @ 500
                                                  SELL 15 @ 520 (C;O) → closes 10, opens 5 short
                                                  BUY 5 @ 530      → closes the 5 short
  S6  Zero-PnL breakeven close             GOOG  BUY 3 @ 100 → SELL 3 @ 100 (pnlRealized=0, C)
  S7  Same-timestamp multi-lot close       AMZN  BUY 10@200, BUY 5@202 → SELL 10@210, SELL 5@210

``synthetic_year2.xml``  (calendar year 2025)
  S3c Cross-year close                     TSLA  SELL 5 @ 120
  S4c Post-split close (new conid=222)     SPLK  CorporateAction RS 100→10, SELL 10 @ 80

Ground-truth expected values (computed below from the in-memory aggregator,
NOT from a hard-coded constant) ensure that the DB import path produces the
same result as a single-pass in-memory run.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest

from app.utils.parsers.aggregator import (
    aggregate_executions_fifo,
    logical_executions_to_trade_creates,
)
from app.utils.parsers.ibkr_xml import IBKRXMLParser

_FIXTURES_DIR = Path(__file__).parent / "fixtures" / "ibkr"
_YEAR1_XML = _FIXTURES_DIR / "synthetic_year1.xml"
_YEAR2_XML = _FIXTURES_DIR / "synthetic_year2.xml"

_Q8 = Decimal("0.00000001")


def _q(v: Decimal) -> Decimal:
    return v.quantize(_Q8, rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# Helpers — in-memory ground truth
# ---------------------------------------------------------------------------


def _parse_both_files() -> tuple[list, list]:
    """Parse both fixture files and return (raw_records, corp_actions)."""
    parser = IBKRXMLParser()
    raw1, ca1 = parser.parse_raw(_YEAR1_XML.read_bytes(), _YEAR1_XML.name)
    raw2, ca2 = parser.parse_raw(_YEAR2_XML.read_bytes(), _YEAR2_XML.name)
    all_raw = sorted(raw1 + raw2, key=lambda r: (r.executed_at, r.id))
    all_ca = ca1 + ca2
    return all_raw, all_ca


def _ground_truth_trades() -> list:
    """Return in-memory FIFO-aggregated trades from both fixture files."""
    all_raw, all_ca = _parse_both_files()
    trade_creates = logical_executions_to_trade_creates(all_raw)
    return aggregate_executions_fifo(trade_creates, corporate_actions=all_ca)


# ---------------------------------------------------------------------------
# Unit tests — pure in-memory FIFO, no DB required
# ---------------------------------------------------------------------------


def test_fixtures_parse_without_errors() -> None:
    """Both XML fixture files must parse cleanly with zero warnings."""
    parser = IBKRXMLParser()
    raw1, ca1 = parser.parse_raw(_YEAR1_XML.read_bytes(), _YEAR1_XML.name)
    assert parser.warnings == [], f"Year1 parse warnings: {parser.warnings}"
    assert len(raw1) == 16, f"Expected 16 raw records from year1, got {len(raw1)}"

    raw2, ca2 = parser.parse_raw(_YEAR2_XML.read_bytes(), _YEAR2_XML.name)
    assert parser.warnings == [], f"Year2 parse warnings: {parser.warnings}"
    assert len(raw2) == 2, f"Expected 2 raw records from year2, got {len(raw2)}"
    assert len(ca2) == 1, f"Expected 1 corporate action from year2, got {len(ca2)}"

    splk_ca = ca2[0]
    assert splk_ca.symbol == "SPLK"
    assert splk_ca.ratio == Decimal("0.1"), f"Expected ratio 0.1, got {splk_ca.ratio}"
    assert splk_ca.old_conid == "111"
    assert splk_ca.new_conid == "222"


def test_s6_zero_pnl_closing_exec_is_treated_as_close() -> None:
    """openCloseIndicator=C with fifoPnlRealized=0 must be a closing leg.

    Before the fix the parser set pnl=None for any execution with
    fifoPnlRealized=0, which caused the FIFO to treat a breakeven close as a
    new opening — producing a sentinel entry_price (0.001) and wrong PnL.
    """
    parser = IBKRXMLParser()
    raw, _ = parser.parse_raw(_YEAR1_XML.read_bytes(), _YEAR1_XML.name)

    goog_sell = next(
        (r for r in raw if r.symbol == "GOOG" and str(r.direction).upper() == "SHORT"),
        None,
    )
    assert goog_sell is not None, "GOOG SELL raw record not found"
    # After the fix: pnl must be Decimal("0"), not None, for a pure-close with
    # fifoPnlRealized=0.
    assert goog_sell.pnl == Decimal("0"), (
        f"Expected pnl=0 for GOOG breakeven close, got {goog_sell.pnl!r}. openCloseIndicator=C should force pnl=Decimal('0') even when fifoPnlRealized=0."
    )


def test_s5_co_mixed_execution_flag_is_set() -> None:
    """The C;O NFLX execution must carry is_mixed_execution=True."""
    parser = IBKRXMLParser()
    raw, _ = parser.parse_raw(_YEAR1_XML.read_bytes(), _YEAR1_XML.name)

    nflx_co = next(
        (r for r in raw if r.symbol == "NFLX" and r.is_mixed_execution),
        None,
    )
    assert nflx_co is not None, "No NFLX raw record with is_mixed_execution=True found. C;O openCloseIndicator must set is_mixed_execution."
    assert nflx_co.quantity == Decimal("15"), f"Expected qty=15 for the C;O NFLX record, got {nflx_co.quantity}"


def test_all_positions_closed_after_both_files() -> None:
    """After aggregating both fixture files there must be no open positions."""
    trades = _ground_truth_trades()
    open_trades = [t for t in trades if t.closed_at is None]
    assert open_trades == [], f"Expected 0 open positions, got {len(open_trades)}: " + ", ".join(t.symbol for t in open_trades)


def test_s1_aapl_simple_roundtrip() -> None:
    """S1: AAPL BUY 10 @ 150 → SELL 10 @ 155.  gross=50, net=49."""
    trades = _ground_truth_trades()
    aapl = [t for t in trades if t.symbol == "AAPL" and t.closed_at]
    assert len(aapl) == 1, f"Expected 1 AAPL trade, got {len(aapl)}"
    t = aapl[0]
    assert t.quantity == Decimal("10")
    assert t.entry_price == Decimal("150")
    assert t.exit_price == Decimal("155")
    assert _q(t.pnl) == Decimal("50.00000000")
    assert _q(t.net_pnl) == Decimal("49.00000000")


def test_s2_msft_partial_close() -> None:
    """S2: MSFT BUY 20 @ 200 → SELL 10 @ 210, SELL 10 @ 220 (two trades)."""
    trades = _ground_truth_trades()
    msft = sorted(
        [t for t in trades if t.symbol == "MSFT" and t.closed_at],
        key=lambda t: t.exit_price or Decimal(0),
    )
    assert len(msft) == 2, f"Expected 2 MSFT trades, got {len(msft)}"
    assert _q(msft[0].net_pnl) == Decimal("99.25000000")  # 10×(210-200) - 0.25 - 0.25
    assert _q(msft[1].net_pnl) == Decimal("199.25000000")  # 10×(220-200) - 0.25 - 0.25


def test_s3_tsla_cross_year_close() -> None:
    """S3: TSLA opened 2024-11-01 @ 100, closed 2025-02-01 @ 120.  net=98."""
    trades = _ground_truth_trades()
    tsla = [t for t in trades if t.symbol == "TSLA" and t.closed_at]
    assert len(tsla) == 1, f"Expected 1 TSLA trade, got {len(tsla)}"
    t = tsla[0]
    assert t.opened_at.year == 2024
    assert t.closed_at is not None and t.closed_at.year == 2025
    assert t.entry_price == Decimal("100")
    assert t.exit_price == Decimal("120")
    assert _q(t.net_pnl) == Decimal("98.00000000")


def test_s4_splk_reverse_split_cross_year_close() -> None:
    """S4: SPLK BUY 100 @ 10 (conid=111) → 10:1 RS → SELL 10 @ 80 (conid=222).

    After the 0.1 ratio reverse split:
      qty   100 × 0.1  =  10
      entry  10 / 0.1  = 100
    Gross PnL = (80 - 100) × 10 = -200.
    """
    trades = _ground_truth_trades()
    splk = [t for t in trades if t.symbol == "SPLK" and t.closed_at]
    assert len(splk) == 1, f"Expected 1 SPLK trade, got {len(splk)}"
    t = splk[0]
    assert t.quantity == Decimal("10"), f"Expected qty=10 post-split, got {t.quantity}"
    assert t.entry_price == Decimal("100"), f"Expected split-adjusted entry=100, got {t.entry_price}"
    assert t.exit_price == Decimal("80")
    assert _q(t.pnl) == Decimal("-200.00000000")


def test_s5_nflx_co_flip_produces_two_trades() -> None:
    """S5: NFLX C;O flip produces exactly 2 closed trades with correct PnL.

    LONG 10 @ 500 → SELL 15 @ 520 (C;O) → BUY 5 @ 530
    Trade 1: LONG  10 @ 500 → exit 520  gross=200, net=199 (comm 0.50+0.50)
    Trade 2: SHORT  5 @ 520 → exit 530  gross=-50, net=-50.50 (comm 0.25+0.25)
    """
    trades = _ground_truth_trades()
    nflx = [t for t in trades if t.symbol == "NFLX" and t.closed_at]
    assert len(nflx) == 2, f"Expected 2 NFLX trades, got {len(nflx)}"

    long_trade = next((t for t in nflx if t.direction.value == "LONG"), None)
    short_trade = next((t for t in nflx if t.direction.value == "SHORT"), None)
    assert long_trade is not None
    assert short_trade is not None

    assert _q(long_trade.net_pnl) == Decimal("199.00000000")
    assert long_trade.entry_price == Decimal("500")
    assert long_trade.exit_price == Decimal("520")

    # The short was opened at 520 (the flip price) and closed at 530.
    assert short_trade.entry_price == Decimal("520"), (
        f"SHORT entry should be 520 (C;O flip price), got {short_trade.entry_price}. This indicates the C;O remainder was mis-classified as orphaned."
    )
    assert short_trade.exit_price == Decimal("530")
    assert _q(short_trade.net_pnl) == Decimal("-50.50000000")


def test_s6_goog_zero_pnl_breakeven_close() -> None:
    """S6: GOOG BUY 3 @ 100 → SELL 3 @ 100 (breakeven close, pnlRealized=0).

    The SELL has openCloseIndicator='C' and fifoPnlRealized=0.  Before the fix
    the parser set pnl=None for this execution, causing the FIFO to treat it as
    an opening SHORT instead of a closing LONG — resulting in 2 orphaned trades
    with sentinel entry prices.  After the fix it produces exactly 1 LONG trade
    with gross_pnl=0 and net_pnl=-0.20 (commissions only).
    """
    trades = _ground_truth_trades()
    goog = [t for t in trades if t.symbol == "GOOG" and t.closed_at]
    assert len(goog) == 1, f"Expected 1 GOOG trade, got {len(goog)}. Multiple trades indicate the breakeven close was mishandled."
    t = goog[0]
    assert t.entry_price != Decimal("0.001"), "Sentinel entry_price detected: breakeven close was treated as orphaned."
    assert t.entry_price == Decimal("100")
    assert t.exit_price == Decimal("100")
    assert t.pnl == Decimal("0"), f"Expected gross_pnl=0, got {t.pnl}"
    assert _q(t.net_pnl) == Decimal("-0.20000000")


def test_s7_amzn_same_timestamp_lots_fifo_order() -> None:
    """S7: AMZN two lots opened at the same timestamp; FIFO matches by txid order.

    Lot A: BUY 10 @ 200  txid=1060
    Lot B: BUY  5 @ 202  txid=1061  (same timestamp, higher txid → FIFO second)
    Close1: SELL 10 @ 210  txid=1062 → closes lot A (FIFO)
    Close2: SELL  5 @ 210  txid=1063 → closes lot B
    """
    trades = _ground_truth_trades()
    amzn = sorted(
        [t for t in trades if t.symbol == "AMZN" and t.closed_at],
        key=lambda t: t.entry_price or Decimal(0),
    )
    assert len(amzn) == 2, f"Expected 2 AMZN trades, got {len(amzn)}"

    lot_a = amzn[0]  # entry=200
    lot_b = amzn[1]  # entry=202
    assert lot_a.entry_price == Decimal("200")
    assert lot_a.quantity == Decimal("10")
    assert _q(lot_a.net_pnl) == Decimal("99.00000000")  # 10×(210-200) - 0.50 - 0.50

    assert lot_b.entry_price == Decimal("202")
    assert lot_b.quantity == Decimal("5")
    assert _q(lot_b.net_pnl) == Decimal("39.50000000")  # 5×(210-202) - 0.25 - 0.25


def test_yearly_pnl_totals_match_ground_truth() -> None:
    """Yearly net PnL totals from the FIFO must match per-year ground truth.

    This is the roll-up assertion: if individual scenario tests pass but a
    cross-trade interaction is wrong, this will catch it.
    """
    trades = _ground_truth_trades()
    by_year: dict[int, Decimal] = defaultdict(Decimal)
    for t in trades:
        if t.closed_at is None:
            continue
        value = t.net_pnl if t.net_pnl is not None else t.pnl
        if value is not None:
            by_year[t.closed_at.year] += _q(value)

    assert by_year[2024] == Decimal("634.30000000"), f"2024 net PnL mismatch: {by_year[2024]}"
    assert by_year[2025] == Decimal("-102.55000000"), f"2025 net PnL mismatch: {by_year[2025]}"


# ---------------------------------------------------------------------------
# Integration tests — sequential DB import via ImportService
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_sequential_import_matches_ground_truth_synthetic(
    client,
    db_session,
) -> None:
    """Sequential DB import of both fixture files must match in-memory GT.

    This is the full-stack regression test for the raw-pipeline sequential
    import.  It imports year1 first, commits, then year2 — mimicking a real
    user who uploads files one by one.

    If this test fails after a refactoring, the production import is broken.
    Do NOT change expected values; fix the code.
    """
    import uuid

    from sqlalchemy import select

    from app.models.trade import Trade
    from app.services.import_service import ImportService
    from app.utils.parsers.factory import BrokerType

    _REGISTER_URL = "/api/v1/auth/register"
    _TOKEN_URL = "/api/v1/auth/token"
    _PORTFOLIOS_URL = "/api/v1/portfolios"

    # --- setup user / portfolio / account ---
    suffix = uuid.uuid4().hex[:8]
    reg = await client.post(
        _REGISTER_URL,
        json={
            "username": f"syn_{suffix}",
            "email": f"syn_{suffix}@test.com",
            "password": "Synthetic@99",
        },
    )
    assert reg.status_code == 201, reg.text
    user_id = uuid.UUID(reg.json()["data"]["id"])

    login = await client.post(
        _TOKEN_URL,
        data={"username": f"syn_{suffix}", "password": "Synthetic@99"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    portfolio_resp = await client.post(
        _PORTFOLIOS_URL,
        headers=headers,
        json={"name": "Synthetic GT", "base_currency": "USD"},
    )
    assert portfolio_resp.status_code == 201, portfolio_resp.text
    portfolio_id = uuid.UUID(portfolio_resp.json()["data"]["id"])

    account_resp = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/accounts",
        headers=headers,
        json={"name": "Synthetic IBKR", "type": "ibkr", "currency": "USD"},
    )
    assert account_resp.status_code == 201, account_resp.text
    account_id = uuid.UUID(account_resp.json()["data"]["id"])

    # --- sequential import ---
    svc = ImportService(db_session)
    for xml_path in [_YEAR1_XML, _YEAR2_XML]:
        await svc.import_file(
            content=xml_path.read_bytes(),
            filename=xml_path.name,
            broker=BrokerType.IBKR,
            portfolio_id=portfolio_id,
            account_id=account_id,
            user_id=user_id,
        )
        await db_session.commit()

    # --- fetch DB trades ---
    result = await db_session.execute(
        select(Trade).where(
            Trade.user_id == user_id,
            Trade.account_id == account_id,
            Trade.closed_at.is_not(None),
        )
    )
    db_trades = result.scalars().all()

    # --- compute in-memory ground truth ---
    gt_trades = _ground_truth_trades()
    gt_by_year: dict[int, Decimal] = defaultdict(Decimal)
    for t in gt_trades:
        if t.closed_at is None:
            continue
        v = t.net_pnl if t.net_pnl is not None else t.pnl
        if v is not None:
            gt_by_year[t.closed_at.year] += _q(v)

    # --- compare ---
    db_by_year: dict[int, Decimal] = defaultdict(Decimal)
    for t in db_trades:
        if t.closed_at is None:
            continue
        v = t.net_pnl if t.net_pnl is not None else t.pnl
        if v is not None:
            db_by_year[t.closed_at.year] += _q(v)

    for year in sorted(gt_by_year.keys()):
        assert abs(db_by_year[year] - gt_by_year[year]) < Decimal("0.01"), (
            f"Year {year}: DB={db_by_year[year]} GT={gt_by_year[year]} diff={abs(db_by_year[year] - gt_by_year[year])}"
        )

    # Spot-check: no sentinel entry prices
    for t in db_trades:
        assert t.entry_price != Decimal("0.001"), f"Sentinel entry_price on {t.symbol}: orphaned lot mis-classification at closed_at={t.closed_at}"
