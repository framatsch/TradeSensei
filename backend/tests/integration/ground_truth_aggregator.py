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

"""Standalone yearly PnL ground-truth generator for IBKR Flex XML files.

The script mirrors the production import math in an offline context:

- Parse XML through :class:`~app.utils.parsers.ibkr_xml.IBKRXMLParser.parse_raw`.
- Aggregate executions with :func:`aggregate_executions_fifo`.
- Sum closed trade PnL by year (preferring ``net_pnl``, fallback ``pnl``).

This produces a deterministic yearly baseline used by integration tests to
verify DB import aggregation results.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from app.schemas.broker_raw_transaction import BrokerRawTransactionCreate
from app.schemas.corporate_action import CorporateActionCreateRequest
from app.schemas.trade import TradeCreate
from app.utils.parsers.aggregator import (
    aggregate_executions_fifo,
    logical_executions_to_trade_creates,
)
from app.utils.parsers.ibkr_xml import IBKRXMLParser

_Q8 = Decimal("0.00000001")


def _quantize_db(value: Decimal) -> Decimal:
    """Quantize numeric values to DB scale (NUMERIC(..., 8))."""
    return value.quantize(_Q8, rounding=ROUND_HALF_UP)


def _parse_raw_files(
    paths: Iterable[Path],
) -> tuple[
    list[BrokerRawTransactionCreate],
    list[CorporateActionCreateRequest],
]:
    """Parse XML files into raw executions and corporate actions."""
    parser = IBKRXMLParser()
    raw_records: list[BrokerRawTransactionCreate] = []
    corporate_actions: list[CorporateActionCreateRequest] = []
    seen_raw_ids: set[str] = set()

    for path in paths:
        raw, ca = parser.parse_raw(path.read_bytes(), filename=path.name)
        corporate_actions.extend(ca)
        for record in raw:
            if record.id in seen_raw_ids:
                continue
            seen_raw_ids.add(record.id)
            raw_records.append(record)

    return raw_records, corporate_actions


def _stable_sort_executions(
    records: list[BrokerRawTransactionCreate],
) -> list[BrokerRawTransactionCreate]:
    """Sort like production logical execution fetch order."""
    return sorted(records, key=lambda r: (r.executed_at, r.id))


def aggregate_files_yearly(paths: Iterable[Path]) -> dict[str, dict]:
    """Aggregate yearly net PnL across multiple Flex Query XML files.

    Only trade-level net P&L is included (entry/exit prices minus per-trade
    commissions).  Platform-level FEE cash transactions (FX conversion
    commissions, market data subscriptions, etc.) are intentionally excluded
    because they are not associated with individual trades and are reported
    separately in the cash transactions view.
    """
    raw_records, corporate_actions = _parse_raw_files(paths)

    sorted_raw_records = _stable_sort_executions(raw_records)
    execution_trades: list[TradeCreate] = logical_executions_to_trade_creates(
        sorted_raw_records
    )
    aggregated_trades = aggregate_executions_fifo(
        execution_trades, corporate_actions=corporate_actions
    )

    yearly_total: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    yearly_trades: dict[int, int] = defaultdict(int)

    for trade in aggregated_trades:
        if trade.closed_at is None:
            continue
        value = trade.net_pnl if trade.net_pnl is not None else trade.pnl
        if value is not None:
            yearly_total[trade.closed_at.year] += _quantize_db(value)
            yearly_trades[trade.closed_at.year] += 1

    return {
        year: {"pnl": _quantize_db(value), "trades": yearly_trades[year]}
        for year, value in sorted(yearly_total.items(), key=lambda kv: kv[0])
    }


def _default_paths() -> list[Path]:
    """Return project-default historical XML file paths."""
    base = Path(__file__).resolve().parent
    return [
        base / "TraderJournal_2023.xml",
        base / "TraderJournal_2024.xml",
        base / "TraderJournal_2025.xml",
        base / "TraderJournal_Q1_2026.xml",
    ]


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Compute yearly ground-truth PnL from IBKR Flex XML files."
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="XML file paths. If omitted, default TraderJournal_*.xml files are used.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON output instead of a text table.",
    )
    args = parser.parse_args()

    file_paths = [Path(p) for p in args.files] if args.files else _default_paths()
    existing_paths = [p for p in file_paths if p.exists()]

    if not existing_paths:
        raise SystemExit("No XML files found.")

    yearly = aggregate_files_yearly(existing_paths)

    if args.json:
        payload = {str(year): str(value) for year, value in yearly.items()}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return

    print("Yearly ground-truth net PnL")
    for year, value in yearly.items():
        print(f"{year}: PnL={value['pnl']} (Trades={value['trades']})")


if __name__ == "__main__":
    main()
