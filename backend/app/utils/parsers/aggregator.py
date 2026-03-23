"""Execution-to-Trade aggregation logic for broker parsers.

Many brokers (like IBKR) report trades on a per-execution basis. If a user
buys 100 shares and later sells 100 shares, the broker reports two separate
records. The journaling platform needs to view this as a single round-trip
position with an entry and an exit.

This module provides a FIFO-based execution aggregator to stitch these back
together.  When corporate actions (stock splits / reverse splits) are provided,
the aggregator applies the ratio adjustments to all open lots for the affected
symbol at the correct chronological point — before matching any subsequent
closing executions.

Seed lots (existing open DB trades) can be supplied via *seed_open_lots* so
that a cross-period import correctly closes positions that were opened in a
previous import.  When a seed lot is closed, the resulting :class:`TradeCreate`
carries the original ``db_trade_id`` so the caller can issue an UPDATE instead
of an INSERT.
"""

import logging
import uuid
from collections import deque
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Protocol

from app.models.trade import Direction
from app.schemas.trade import TradeCreate

logger = logging.getLogger(__name__)


class CorporateActionLike(Protocol):
    """Structural protocol for corporate-action objects accepted by the aggregator.

    Any object that exposes these five attributes is accepted.  Both the real
    :class:`~app.models.corporate_action.CorporateAction` ORM model and
    lightweight test stubs satisfy this protocol.
    """

    symbol: str
    date: date
    ratio: Decimal
    old_conid: str | None
    new_conid: str | None


class SeedLotLike(Protocol):
    """Structural protocol for existing open DB trades used to seed the aggregator.

    Any object exposing these attributes is accepted (the ORM
    :class:`~app.models.trade.Trade` satisfies this protocol).
    """

    id: uuid.UUID
    symbol: str
    broker_conid: str | None
    asset_class: str  # AssetClass StrEnum or its string value
    quantity: Decimal
    entry_price: Decimal
    commission: Decimal
    opened_at: datetime
    direction: str  # Direction StrEnum or its string value


def _date_to_datetime(d: date) -> datetime:
    """Convert a :class:`date` to a timezone-aware :class:`datetime` at midnight UTC.

    Args:
        d: The date to convert.

    Returns:
        A UTC-aware :class:`datetime` at midnight of the given date.
    """
    return datetime(d.year, d.month, d.day, tzinfo=UTC)


def aggregate_executions_fifo(
    executions: list[TradeCreate],
    symbol_map: dict[str, str] | None = None,
    conid_map: dict[str, str] | None = None,
    corporate_actions: Sequence[CorporateActionLike] | None = None,
    seed_open_lots: Sequence[SeedLotLike] | None = None,
) -> list[TradeCreate]:
    """Group execution-level TradeCreate objects into round-trip TradeCreate objects.

    Executions must be chronologically ordered. Maintains a FIFO queue of open lots
    per instrument. Instruments are identified primarily by ``broker_conid``
    (if available) or ``(symbol, asset_class)``.

    When *corporate_actions* are provided, split/reverse-split events are woven into
    the chronological event stream. Each split event adjusts all open lots for the
    affected symbol at the exact moment the event occurs:

    - ``lot.quantity  *= ratio``
    - ``lot.entry_price /= ratio``

    If the corporate action includes an ``old_conid`` → ``new_conid`` mapping, the
    internal queue key is re-keyed so that subsequent executions arriving with the
    new conid are matched to the correct open lots.

    When *seed_open_lots* are provided, they are pre-loaded into the FIFO queue
    **before** any executions are processed.  This allows a cross-period import to
    correctly close positions that were opened in a prior import.  Each seed lot's
    ``db_trade_id`` is set to its original database ``id`` so that the caller can
    issue an UPDATE (rather than an INSERT) for those lots when they are closed.

    Args:
        executions: A list of :class:`~app.schemas.trade.TradeCreate` representing
            individual executions.
        symbol_map: Optional mapping to normalize symbols (e.g., for corporate actions).
        conid_map: Optional mapping to normalize broker contract IDs (e.g., for splits).
        corporate_actions: Optional sequence of objects satisfying
            :class:`CorporateActionLike` that should be applied during aggregation.
            When *None* or empty the behaviour is identical to the previous
            implementation (backward compatible).
        seed_open_lots: Optional sequence of objects satisfying :class:`SeedLotLike`
            representing open trades already stored in the database.  When supplied,
            these are pre-populated into the FIFO queue so that incoming closing
            executions can be matched against them.  Closed results originating from
            a seed lot will have ``db_trade_id`` set to the seed's database ``id``.

    Returns:
        A list of aggregated round-trip :class:`~app.schemas.trade.TradeCreate`
        objects.
    """
    # Sort executions chronologically
    sorted_execs = sorted(executions, key=lambda x: x.opened_at)

    # Sort corporate actions chronologically (earliest first)
    sorted_cas: list[CorporateActionLike] = (
        sorted(corporate_actions, key=lambda c: c.date) if corporate_actions else []
    )

    # open_lots: queue keyed by (symbol, conid, asset_class)
    open_lots: dict[tuple[str, str | None, str], deque[TradeCreate]] = {}
    completed_trades: list[TradeCreate] = []

    # Pre-populate the queue with seed lots from the DB (existing open positions).
    if seed_open_lots:
        for seed in sorted(seed_open_lots, key=lambda s: s.opened_at):
            seed_symbol = seed.symbol
            if symbol_map and seed_symbol in symbol_map:
                seed_symbol = symbol_map[seed_symbol]
            seed_conid = seed.broker_conid
            if conid_map and seed_conid in conid_map:
                seed_conid = conid_map[seed_conid]

            # asset_class and direction are StrEnums — str() gives the canonical value
            asset_class_val: str = str(seed.asset_class)
            key: tuple[str, str | None, str] = (
                seed_symbol,
                seed_conid,
                asset_class_val,
            )
            if key not in open_lots:
                open_lots[key] = deque()

            # Build a TradeCreate that mirrors the seed lot; tag it with its DB id.
            from app.models.trade import AssetClass  # local import to avoid circular

            opened_at = seed.opened_at
            if opened_at.tzinfo is None:
                opened_at = opened_at.replace(tzinfo=UTC)

            seed_tc = TradeCreate(
                user_id=None,
                symbol=seed_symbol,
                direction=Direction(seed.direction),
                asset_class=AssetClass(seed.asset_class),
                quantity=seed.quantity,
                entry_price=seed.entry_price,
                commission=seed.commission,
                opened_at=opened_at,
                broker_conid=seed_conid,
                db_trade_id=seed.id,
            )
            open_lots[key].append(seed_tc)

    # Two-pointer merge: advance through executions; apply any split events whose
    # date falls at or before the current execution's date first.
    ca_idx = 0

    for exec_trade in sorted_execs:
        exec_date = exec_trade.opened_at.date()

        # Apply all split events that happened *before* this execution (or on the
        # same day — splits take effect at market open).
        while ca_idx < len(sorted_cas) and sorted_cas[ca_idx].date <= exec_date:
            _apply_split_event(open_lots, sorted_cas[ca_idx])
            ca_idx += 1

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
                # It's an orphaned closing leg (open leg was before the export period).
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

        # Task 4.4 — Warn when quantity discrepancy may indicate an unregistered split.
        # If the closing execution quantity significantly exceeds what is in the queue,
        # emit a warning so the user knows to check for a missed split event.
        total_open_qty = sum(lot.quantity for lot in queue)
        if exec_trade.pnl is not None and exec_qty_remaining > total_open_qty * Decimal(
            "2"
        ):
            logger.warning(
                "Possible unregistered split for symbol '%s': "
                "closing execution quantity "
                "(%s) is more than 2x the open lot quantity (%s). "
                "Consider adding a Corporate Action for this symbol.",
                symbol,
                exec_qty_remaining,
                total_open_qty,
            )

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

    # Apply any trailing corporate actions that occurred after the last execution
    while ca_idx < len(sorted_cas):
        _apply_split_event(open_lots, sorted_cas[ca_idx])
        ca_idx += 1

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


def _apply_split_event(
    open_lots: dict[tuple[str, str | None, str], deque[TradeCreate]],
    ca: CorporateActionLike,
) -> None:
    """Apply a split event to all open lots for the affected symbol.

    For every lot in *open_lots* whose queue key matches *ca.symbol* (and
    optionally *ca.old_conid*), adjust quantity and entry price by the split
    ratio:

    - ``lot.quantity  *= ca.ratio``
    - ``lot.entry_price /= ca.ratio``

    If *ca.old_conid* and *ca.new_conid* are both set, the queue is also
    re-keyed from ``(symbol, old_conid, asset_class)`` to
    ``(symbol, new_conid, asset_class)`` so that subsequent executions
    arriving with the new conid are matched to the adjusted lots.

    Args:
        open_lots: The mutable open-lots dictionary from the aggregator loop.
        ca: An object satisfying :class:`CorporateActionLike` to apply.
    """
    keys_to_remap: list[
        tuple[tuple[str, str | None, str], tuple[str, str | None, str]]
    ] = []

    for key, queue in open_lots.items():
        key_symbol, key_conid, key_asset_class = key

        # Match by symbol; also match by old_conid when provided.
        symbol_match = key_symbol == ca.symbol
        conid_match = (
            ca.old_conid is None  # no conid filter → match any conid for this symbol
            or key_conid == ca.old_conid
        )
        if not (symbol_match and conid_match):
            continue

        if not queue:
            continue

        # Adjust all lots in this queue
        for lot in queue:
            lot.quantity = lot.quantity * ca.ratio
            lot.entry_price = lot.entry_price / ca.ratio
            # Update the conid stored in each lot to the new conid (if provided)
            if ca.new_conid is not None:
                lot.broker_conid = ca.new_conid

        logger.debug(
            "Applied split ratio=%s for symbol '%s' to %d open lot(s) (key=%s).",
            ca.ratio,
            ca.symbol,
            len(queue),
            key,
        )

        # Schedule queue re-keying if conid changed
        if ca.old_conid is not None and ca.new_conid is not None:
            new_key: tuple[str, str | None, str] = (
                key_symbol,
                ca.new_conid,
                key_asset_class,
            )
            if new_key != key:
                keys_to_remap.append((key, new_key))

    # Re-key outside the iteration to avoid mutating dict while iterating
    for old_key, new_key in keys_to_remap:
        existing_queue = open_lots.pop(old_key)
        if new_key in open_lots:
            # Merge: extend the existing new-key queue (shouldn't happen in practice)
            open_lots[new_key].extend(existing_queue)
            logger.warning(
                "Conid remap collision: merging queues for old_key=%s into new_key=%s. "
                "This may indicate duplicate corporate actions.",
                old_key,
                new_key,
            )
        else:
            open_lots[new_key] = existing_queue
        logger.debug("Re-keyed open lots queue from %s → %s.", old_key, new_key)
