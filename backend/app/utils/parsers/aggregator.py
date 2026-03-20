"""Execution-to-Trade aggregation logic for broker parsers.

Many brokers (like IBKR) report trades on a per-execution basis. If a user
buys 100 shares and later sells 100 shares, the broker reports two separate
records. The journaling platform needs to view this as a single round-trip
position with an entry and an exit.

This module provides a FIFO-based execution aggregator to stitch these back
together.
"""

from collections import deque
from decimal import Decimal

from app.models.trade import Direction
from app.schemas.trade import TradeCreate


def aggregate_executions_fifo(
    executions: list[TradeCreate],
    symbol_map: dict[str, str] | None = None,
    conid_map: dict[str, str] | None = None,
) -> list[TradeCreate]:
    """Group execution-level TradeCreate objects into round-trip TradeCreate objects.

    Executions must be chronologically ordered. Maintains a FIFO queue of open lots
    per instrument. Instruments are identified primarily by ``broker_conid`` (if available)
    or ``(symbol, asset_class)``.

    Args:
        executions: A list of :class:`~app.schemas.trade.TradeCreate` representing
            individual executions.
        symbol_map: Optional mapping to normalize symbols (e.g., for corporate actions).
        conid_map: Optional mapping to normalize broker contract IDs (e.g., for splits).

    Returns:
        A list of aggregated round-trip :class:`~app.schemas.trade.TradeCreate`
        objects.
    """
    # Sort chronologically just in case
    sorted_execs = sorted(executions, key=lambda x: x.opened_at)

    open_lots: dict[tuple[str, str | None, str], deque[TradeCreate]] = {}
    completed_trades: list[TradeCreate] = []

    for exec_trade in sorted_execs:
        # Normalize identification
        symbol = exec_trade.symbol
        if symbol_map and symbol in symbol_map:
            symbol = symbol_map[symbol]

        conid = exec_trade.broker_conid
        if conid_map and conid in conid_map:
            conid = conid_map[conid]

        # Primary key: (symbol, conid, asset_class)
        # Using symbol and conid together provides robustness against re-used IDs
        # or symbol changes where conid remains same (or vice versa).
        key = (symbol, conid, exec_trade.asset_class)

        if key not in open_lots:
            open_lots[key] = deque()

        queue = open_lots[key]
        is_closing_leg = exec_trade.pnl is not None

        # If queue is empty, or the execution is in the same direction as the open lots,
        # it increases the position (unless it's explicitly marked as closing via pnl).
        if not queue or queue[0].direction == exec_trade.direction:
            if not is_closing_leg:
                # Update normalized symbol/conid in the copy
                stored_trade = exec_trade.model_copy(
                    update={"symbol": symbol, "broker_conid": conid}
                )
                queue.append(stored_trade)
            else:
                from datetime import timedelta

                # It's an orphaned closing leg (the open leg was before the export period).
                # Reconstruct a closed trade.
                orig_direction = (
                    Direction.LONG
                    if exec_trade.direction == Direction.SHORT
                    else Direction.SHORT
                )
                opened_at = exec_trade.opened_at
                closed_at = exec_trade.closed_at or exec_trade.opened_at
                if closed_at <= opened_at:
                    closed_at = opened_at + timedelta(seconds=1)

                orphaned_trade = exec_trade.model_copy(
                    update={
                        "symbol": symbol,
                        "broker_conid": conid,
                        "direction": orig_direction,
                        "entry_price": Decimal("0.001"),  # Sentinel tiny value
                        "exit_price": exec_trade.entry_price,
                        "opened_at": opened_at,
                        "closed_at": closed_at,
                        "pnl": exec_trade.pnl,
                    }
                )
                completed_trades.append(orphaned_trade)
            continue

        # The execution is in the opposite direction. It closes open lots.
        exec_qty_remaining = exec_trade.quantity
        exec_pnl_remaining = exec_trade.pnl or Decimal("0")
        exec_commission_remaining = exec_trade.commission

        while exec_qty_remaining > Decimal("0") and queue:
            open_lot = queue[0]
            match_qty = min(open_lot.quantity, exec_qty_remaining)

            lot_comm = (
                (open_lot.commission * match_qty) / open_lot.quantity
                if open_lot.quantity
                else Decimal("0")
            )
            exec_comm = (
                (exec_commission_remaining * match_qty) / exec_qty_remaining
                if exec_qty_remaining
                else Decimal("0")
            )

            matched_pnl: Decimal | None = None
            matched_pnl_eur: Decimal | None = None
            if is_closing_leg and exec_pnl_remaining:
                matched_pnl = (exec_pnl_remaining * match_qty) / exec_qty_remaining
                if exec_trade.pnl_eur is not None:
                    matched_pnl_eur = (
                        exec_trade.pnl_eur * match_qty
                    ) / exec_qty_remaining

            from datetime import timedelta

            closed_at = exec_trade.opened_at
            if closed_at <= open_lot.opened_at:
                closed_at = open_lot.opened_at + timedelta(seconds=1)

            closed_trade = open_lot.model_copy(
                update={
                    "symbol": symbol,
                    "broker_conid": conid,
                    "quantity": match_qty,
                    "exit_price": exec_trade.entry_price,
                    "closed_at": closed_at,  # actual closing time (or bumped)
                    "commission": lot_comm + exec_comm,
                    "pnl": matched_pnl,
                    "pnl_eur": matched_pnl_eur,
                }
            )
            completed_trades.append(closed_trade)

            # Deduct quantities
            exec_qty_remaining -= match_qty
            open_lot.quantity -= match_qty
            open_lot.commission -= lot_comm
            exec_commission_remaining -= exec_comm
            if exec_pnl_remaining:
                exec_pnl_remaining -= matched_pnl or Decimal("0")

            if open_lot.quantity <= Decimal("0"):
                queue.popleft()

        # If there's still execution quantity remaining, it either flipped the position
        # or it's an orphaned closing quantity.
        if exec_qty_remaining > Decimal("0"):
            if is_closing_leg:
                from datetime import timedelta

                # Orphaned closing remainder
                orig_direction = (
                    Direction.LONG
                    if exec_trade.direction == Direction.SHORT
                    else Direction.SHORT
                )
                opened_at = exec_trade.opened_at
                closed_at = exec_trade.closed_at or exec_trade.opened_at
                if closed_at <= opened_at:
                    closed_at = opened_at + timedelta(seconds=1)

                orphaned_trade = exec_trade.model_copy(
                    update={
                        "symbol": symbol,
                        "broker_conid": conid,
                        "direction": orig_direction,
                        "quantity": exec_qty_remaining,
                        "entry_price": Decimal("0.001"),
                        "exit_price": exec_trade.entry_price,
                        "opened_at": opened_at,
                        "closed_at": closed_at,
                        "commission": exec_commission_remaining,
                        "pnl": exec_pnl_remaining if exec_pnl_remaining else None,
                    }
                )
                completed_trades.append(orphaned_trade)
            else:
                # Flipped position -> new open lot
                flipped_lot = exec_trade.model_copy(
                    update={
                        "symbol": symbol,
                        "broker_conid": conid,
                        "quantity": exec_qty_remaining,
                        "commission": exec_commission_remaining,
                        "pnl": None,
                        "closed_at": None,
                        "exit_price": None,
                    }
                )
                queue.append(flipped_lot)

    # Add any remaining open lots to the output
    for queue in open_lots.values():
        for lot in queue:
            # Ensure it looks like an open trade
            lot.exit_price = None
            lot.closed_at = None
            lot.pnl = None
            completed_trades.append(lot)

    # Sort final output by opened_at
    return sorted(completed_trades, key=lambda x: x.opened_at)
