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
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Protocol, cast

from app.models.trade import AssetClass, Direction
from app.schemas.trade import TradeCreate

if TYPE_CHECKING:
    from app.models.trade import Trade

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ExecutionAllocation:
    """Track execution quantity/commission consumed by a trade during FIFO aggregation.

    Used by split-aware execution linking to determine when executions need to be
    split across multiple trades and how to allocate quantities proportionally.
    """

    execution_id: uuid.UUID | str  # Source LogicalExecution ID
    quantity_used: Decimal  # Portion allocated to this trade
    commission_used: Decimal  # Proportional commission
    entry_price: Decimal  # Execution price


@dataclass(slots=True)
class TradeCreateWithSources:
    """Enhanced TradeCreate that tracks its source executions for split-aware linking.

    Used to carry execution allocation information from FIFO aggregation through
    to the import service for proper trade_id backfilling.
    """

    trade_create: TradeCreate
    source_executions: list[ExecutionAllocation]
    created_trade: "Trade | None" = None  # Set after DB insert


@dataclass(slots=True)
class ComboBuildResult:
    """Result bundle returned by :func:`build_combo_positions`.

    Attributes:
        combo_trades: COMBO trades synthesized from combo-eligible executions.
        fifo_executions: Non-combo executions that should continue through FIFO.
        warnings: Non-fatal matching/anomaly warnings.
    """

    combo_trades: list[TradeCreateWithSources]
    fifo_executions: list[TradeCreate]
    warnings: list[str]


@dataclass(slots=True)
class _ComboOrderGroup:
    order_id: str
    legs: list[TradeCreate]


@dataclass(slots=True)
class _OpenComboPosition:
    symbol: str
    order_id: str
    contract_set: tuple[str, ...]
    quantities_by_conid: dict[str, Decimal]
    unit_count: Decimal | None
    remaining_units: Decimal | None
    open_legs: list[TradeCreate]
    close_legs: list[TradeCreate]
    opening_net_cash: Decimal
    db_trade_id: uuid.UUID | None = None
    anomalous_close_attached: bool = False


def _combo_contract_key(legs: Sequence[TradeCreate]) -> tuple[tuple[str, Decimal], ...]:
    quantities: dict[str, Decimal] = {}
    for leg in legs:
        conid = leg.broker_conid
        if conid is None:
            continue
        quantities[conid] = quantities.get(conid, Decimal("0")) + abs(leg.quantity or Decimal("0"))
    return tuple(sorted((conid, qty) for conid, qty in quantities.items()))


def _combo_unit_count(quantities_by_conid: dict[str, Decimal]) -> Decimal | None:
    """Return the common per-leg quantity for a combo order, or ``None`` if legs differ.

    Standard combo orders (verticals, straddles, etc.) execute every leg with the
    same absolute quantity (e.g. BUY 1 / SELL 1). Ratio spreads (e.g. 2:1) have
    differing per-leg quantities and cannot be split unit-by-unit with this simple
    scheme; ``None`` signals the caller to fall back to exact whole-order matching.
    """
    values = set(quantities_by_conid.values())
    if len(values) != 1:
        return None
    return next(iter(values))


def _split_leg_by_fraction(leg: TradeCreate, fraction: Decimal) -> TradeCreate:
    """Return a proportional slice of a combo leg's quantity/commission/pnl/net_cash.

    Used to split a single broker closing execution across multiple FIFO-matched
    open combo positions (e.g. the user scaled into the same spread via two
    separate orders that were later closed together in one order).
    """
    updates: dict[str, object] = {}
    if leg.quantity is not None:
        updates["quantity"] = leg.quantity * fraction
    if leg.commission is not None:
        updates["commission"] = leg.commission * fraction
    if leg.pnl is not None:
        updates["pnl"] = leg.pnl * fraction
    if leg.net_pnl is not None:
        updates["net_pnl"] = leg.net_pnl * fraction
    net_cash = getattr(leg, "net_cash", None)
    if net_cash is not None:
        updates["net_cash"] = cast(Decimal, net_cash) * fraction
    return leg.model_copy(update=updates)


def _derive_combo_direction(opening_net_cash: Decimal) -> Direction:
    # Net cash out (debit) => LONG, net cash in (credit) => SHORT.
    if opening_net_cash > Decimal("0"):
        return Direction.SHORT
    return Direction.LONG


def build_combo_positions(executions: Sequence[TradeCreate]) -> ComboBuildResult:
    """Build COMBO trades from enriched execution rows.

    Expected internal fields on each input execution:
    - ``broker_order_id`` (order-level grouping key)
    - ``open_close`` ("O" | "C" | None)
    - ``broker_conid``
    - ``net_cash``
    - ``source_execution_id``

    Executions that are not combo-eligible are returned unchanged in
    ``fifo_executions``.
    """

    by_order: dict[str, list[TradeCreate]] = {}
    for execution in executions:
        order_id = execution.broker_order_id
        if not order_id:
            continue
        by_order.setdefault(order_id, []).append(execution)

    combo_groups: list[_ComboOrderGroup] = []
    combo_leg_ids: set[uuid.UUID | str] = set()
    for order_id, legs in by_order.items():
        distinct_conids = {leg.broker_conid for leg in legs if leg.broker_conid is not None}
        if len(distinct_conids) < 2:
            continue
        combo_groups.append(_ComboOrderGroup(order_id=order_id, legs=sorted(legs, key=lambda l: l.opened_at)))
        for leg in legs:
            if leg.source_execution_id is not None:
                combo_leg_ids.add(leg.source_execution_id)

    fifo_executions = [
        execution
        for execution in executions
        if execution.source_execution_id not in combo_leg_ids
    ]

    open_positions: list[_OpenComboPosition] = []
    warnings: list[str] = []

    sorted_groups = sorted(
        combo_groups,
        key=lambda group: min((leg.opened_at for leg in group.legs), default=datetime.min.replace(tzinfo=UTC)),
    )

    for group in sorted_groups:
        markers = {getattr(leg, "open_close", None) for leg in group.legs}
        non_null_markers = {marker for marker in markers if marker in {"O", "C"}}
        if len(non_null_markers) != 1:
            warnings.append(
                f"Combo order {group.order_id} has mixed/unknown open_close markers; skipped combo matching for this order."
            )
            continue

        marker = next(iter(non_null_markers))
        contract_key = _combo_contract_key(group.legs)
        contract_set = tuple(conid for conid, _ in contract_key)
        quantities_by_conid = {conid: qty for conid, qty in contract_key}
        symbol = group.legs[0].symbol

        if marker == "O":
            opening_net_cash = sum(
                (
                    cast(Decimal, getattr(leg, "net_cash", Decimal("0")) or Decimal("0"))
                    for leg in group.legs
                ),
                Decimal("0"),
            )
            group_db_trade_id = next((leg.db_trade_id for leg in group.legs if leg.db_trade_id is not None), None)
            unit_count = _combo_unit_count(quantities_by_conid)

            # Each opening order becomes its own distinct combo position — even
            # when an identical contract set is already open for this underlying
            # (e.g. the user scaled into the same spread via two separate orders).
            # A later closing order that spans multiple such positions is matched
            # FIFO and split proportionally below, rather than merging the opens
            # into a single position (which would misrepresent two separate round
            # trips as one).
            open_positions.append(
                _OpenComboPosition(
                    symbol=symbol,
                    order_id=group.order_id,
                    contract_set=contract_set,
                    quantities_by_conid=quantities_by_conid,
                    unit_count=unit_count,
                    remaining_units=unit_count,
                    open_legs=list(group.legs),
                    close_legs=[],
                    opening_net_cash=opening_net_cash,
                    db_trade_id=group_db_trade_id,
                )
            )
            continue

        # marker == "C" => match FIFO against open positions with the same
        # contract set, splitting the closing legs proportionally across
        # multiple open positions when the closing quantity exceeds any single
        # one of them (e.g. two 1-lot opens closed together in one 2-lot order).
        close_unit_count = _combo_unit_count(quantities_by_conid)

        candidates = [
            position
            for position in open_positions
            if position.symbol == symbol
            and position.contract_set == contract_set
            and not position.close_legs
            and (position.remaining_units is None or position.remaining_units > Decimal("0"))
        ]

        if close_unit_count is None or any(position.unit_count is None for position in candidates):
            # Ratio spread (mismatched per-leg quantities) — cannot split
            # unit-by-unit; fall back to exact whole-order matching only.
            matched_position = next(
                (position for position in candidates if position.quantities_by_conid == quantities_by_conid),
                None,
            )
            if matched_position is not None:
                matched_position.close_legs.extend(group.legs)
                matched_position.remaining_units = Decimal("0")
                continue
        else:
            remaining_close_units = close_unit_count
            for position in candidates:
                if remaining_close_units <= Decimal("0"):
                    break
                position_remaining = cast(Decimal, position.remaining_units)
                match_units = min(position_remaining, remaining_close_units)
                if match_units <= Decimal("0"):
                    continue
                fraction = match_units / close_unit_count
                position.close_legs.extend(_split_leg_by_fraction(leg, fraction) for leg in group.legs)
                position.remaining_units = position_remaining - match_units
                remaining_close_units -= match_units

            if remaining_close_units <= Decimal("0"):
                continue

        same_symbol_open = [
            position
            for position in open_positions
            if position.symbol == symbol
            and not position.close_legs
            and (position.remaining_units is None or position.remaining_units > Decimal("0"))
        ]
        expected_sets = [set(position.contract_set) for position in same_symbol_open]
        received_set = set(contract_set)
        warnings.append(
            "Unmatched combo close order "
            f"{group.order_id}: expected one of {expected_sets or '[]'}, received {received_set}."
        )

        # Keep behavior loud and debuggable: do not reroute into FIFO.
        # If exactly one open combo exists for the same underlying, attach anomalous
        # close legs to preserve leg visibility while keeping the position logically open.
        if len(same_symbol_open) == 1:
            same_symbol_open[0].close_legs.extend(group.legs)
            same_symbol_open[0].anomalous_close_attached = True

    combo_trades: list[TradeCreateWithSources] = []
    for position in open_positions:
        legs = [*position.open_legs, *position.close_legs]
        opened_at = min(leg.opened_at for leg in position.open_legs)
        closed_at: datetime | None = None
        if position.close_legs and not position.anomalous_close_attached:
            closed_at = max(leg.opened_at for leg in position.close_legs)

        total_commission = sum(((leg.commission or Decimal("0")) for leg in legs), Decimal("0"))
        closing_pnls = [leg.pnl for leg in position.close_legs if leg.pnl is not None]
        pnl = sum(closing_pnls, Decimal("0")) if closing_pnls and not position.anomalous_close_attached else None
        net_pnl = (pnl - total_commission) if pnl is not None else None

        combo_trade = TradeCreate(
            symbol=position.symbol,
            direction=_derive_combo_direction(position.opening_net_cash),
            is_combo=True,
            asset_class=None,
            quantity=None,
            entry_price=None,
            exit_price=None,
            commission=total_commission,
            opened_at=opened_at,
            closed_at=closed_at,
            pnl=pnl,
            net_pnl=net_pnl,
            currency=position.open_legs[0].currency,
            broker_order_id=position.order_id,
            db_trade_id=position.db_trade_id,
        )

        source_allocations: list[ExecutionAllocation] = []
        for leg in legs:
            if leg.source_execution_id is None:
                continue
            source_allocations.append(
                ExecutionAllocation(
                    execution_id=leg.source_execution_id,
                    quantity_used=leg.quantity or Decimal("0"),
                    commission_used=leg.commission or Decimal("0"),
                    entry_price=leg.entry_price or Decimal("0"),
                )
            )

        combo_trades.append(
            TradeCreateWithSources(
                trade_create=combo_trade,
                source_executions=source_allocations,
            )
        )

    return ComboBuildResult(
        combo_trades=combo_trades,
        fifo_executions=fifo_executions,
        warnings=warnings,
    )


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
    asset_class: AssetClass | str  # AssetClass StrEnum or its string value
    quantity: Decimal
    entry_price: Decimal
    commission: Decimal
    opened_at: datetime
    direction: Direction | str  # Direction StrEnum or its string value
    multiplier: int


class ExecutionLike(Protocol):
    """Structural protocol for per-execution objects that can be aggregated.

    Both :class:`~app.models.logical_execution.LogicalExecution` ORM instances
    and lightweight test stubs satisfy this protocol.  The aggregator accepts
    this type via :func:`logical_executions_to_trade_creates`.
    """

    id: uuid.UUID  # Added for split-aware execution linking
    symbol: str
    conid: str | None
    asset_class: AssetClass | str  # AssetClass StrEnum or its string value
    direction: Direction | str  # Direction StrEnum or its string value
    quantity: Decimal
    price: Decimal
    commission: Decimal
    executed_at: datetime
    pnl: Decimal | None
    multiplier: int


def _date_to_datetime(d: date) -> datetime:
    """Convert a :class:`date` to a timezone-aware :class:`datetime` at midnight UTC.

    Args:
        d: The date to convert.

    Returns:
        A UTC-aware :class:`datetime` at midnight of the given date.
    """
    return datetime(d.year, d.month, d.day, tzinfo=UTC)


def logical_executions_to_trade_creates(
    executions: list[ExecutionLike],
) -> list[TradeCreate]:
    """Convert a list of logical execution objects into :class:`TradeCreate` instances.

    This bridge function allows :func:`aggregate_executions_fifo` to be driven
    by :class:`~app.models.logical_execution.LogicalExecution` ORM rows or any
    object satisfying :class:`ExecutionLike` rather than parser-produced
    :class:`TradeCreate` objects directly.

    The ``opened_at`` field is taken from ``executed_at``.  A ``closed_at``
    offset of +1 second is applied for executions that have a non-``None``
    ``pnl`` (same convention used by the IBKR XML parser).

    Args:
        executions: List of objects satisfying :class:`ExecutionLike`.

    Returns:
        List of :class:`~app.schemas.trade.TradeCreate` ready for
        :func:`aggregate_executions_fifo`.
    """
    return list(iter_logical_executions_to_trade_creates(executions))


def iter_logical_executions_to_trade_creates(
    executions: Iterable[ExecutionLike],
) -> Iterator[TradeCreate]:
    """Yield :class:`TradeCreate` rows from logical execution objects.

    Args:
        executions: Iterable of objects satisfying :class:`ExecutionLike`.

    Yields:
        Converted :class:`TradeCreate` instances in input order.
    """
    from datetime import timedelta

    from app.models.trade import AssetClass

    for ex in executions:
        opened_at = ex.executed_at
        if opened_at.tzinfo is None:
            opened_at = opened_at.replace(tzinfo=UTC)
        closed_at = opened_at + timedelta(seconds=1) if ex.pnl is not None else None
        raw_currency = getattr(ex, "currency", None)
        currency = raw_currency if isinstance(raw_currency, str) else None

        yield TradeCreate(
            symbol=ex.symbol,
            direction=Direction(ex.direction),
            asset_class=AssetClass(ex.asset_class),
            quantity=ex.quantity,
            entry_price=ex.price,
            commission=ex.commission,
            opened_at=opened_at,
            closed_at=closed_at,
            pnl=ex.pnl,
            currency=currency,
            broker_conid=ex.conid,
            multiplier=ex.multiplier,
            is_mixed_execution=getattr(ex, "is_mixed_execution", False),
            source_execution_id=ex.id,
        )


def aggregate_executions_fifo(
    executions: list[TradeCreate],
    symbol_map: dict[str, str] | None = None,
    conid_map: dict[str, str] | None = None,
    corporate_actions: Sequence[CorporateActionLike] | None = None,
    seed_open_lots: Sequence[SeedLotLike] | None = None,
    seed_orphaned_lots: Sequence[SeedLotLike] | None = None,
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
    sorted_cas: list[CorporateActionLike] = sorted(corporate_actions, key=lambda c: c.date) if corporate_actions else []

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
                multiplier=seed.multiplier,
            )
            open_lots[key].append(seed_tc)

    # Two-pointer merge: advance through executions; apply any split events whose
    # date falls at or before the current execution's date first.

    # orphaned_lots: queue keyed by (symbol, conid, asset_class)
    orphaned_lots: dict[tuple[str, str | None, str], deque[TradeCreate]] = {}

    if seed_orphaned_lots:
        for seed in sorted(seed_orphaned_lots, key=lambda s: s.opened_at):
            seed_symbol = seed.symbol
            if symbol_map and seed_symbol in symbol_map:
                seed_symbol = symbol_map[seed_symbol]
            seed_conid = seed.broker_conid
            if conid_map and seed_conid in conid_map:
                seed_conid = conid_map[seed_conid]

            orphaned_asset_class_val: str = str(seed.asset_class)
            orphaned_key: tuple[str, str | None, str] = (
                seed_symbol,
                seed_conid,
                orphaned_asset_class_val,
            )
            if orphaned_key not in orphaned_lots:
                orphaned_lots[orphaned_key] = deque()

            opened_at = seed.opened_at
            if opened_at.tzinfo is None:
                opened_at = opened_at.replace(tzinfo=UTC)

            # seed.closed_at is not part of SeedLotLike protocol,
            # but the DB object has it.
            # We can use getattr just in case.
            closed_at = getattr(seed, "closed_at", None)
            if closed_at and closed_at.tzinfo is None:
                closed_at = closed_at.replace(tzinfo=UTC)

            seed_tc = TradeCreate(
                user_id=None,
                symbol=seed_symbol,
                direction=Direction(seed.direction),
                asset_class=AssetClass(seed.asset_class),
                quantity=seed.quantity,
                entry_price=seed.entry_price,
                exit_price=getattr(seed, "exit_price", None),
                commission=seed.commission,
                opened_at=opened_at,
                closed_at=closed_at,
                pnl=getattr(seed, "pnl", None),
                broker_conid=seed_conid,
                db_trade_id=seed.id,
                multiplier=seed.multiplier,
            )
            orphaned_lots[orphaned_key].append(seed_tc)

    ca_idx = 0

    for exec_trade in sorted_execs:
        exec_date = exec_trade.opened_at.date()

        # Apply all split events that happened *before* this execution (or on the
        # same day — splits take effect at market open).
        while ca_idx < len(sorted_cas) and sorted_cas[ca_idx].date <= exec_date:
            _apply_split_event(open_lots, sorted_cas[ca_idx])
            _apply_split_event(orphaned_lots, sorted_cas[ca_idx])
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
        asset_class_val = str(exec_trade.asset_class)
        key = (symbol, conid, asset_class_val)

        if key not in open_lots:
            open_lots[key] = deque()

        queue = open_lots[key]
        is_closing_leg = exec_trade.pnl is not None

        # If queue is empty, or the execution is in the same direction as the open lots,
        # it increases the position (unless it's explicitly marked as closing via pnl).
        if not queue or queue[0].direction == exec_trade.direction:
            if not is_closing_leg:
                exec_qty_remaining = exec_trade.quantity
                exec_commission_remaining = exec_trade.commission

                stored_trade = exec_trade.model_copy(
                    update={
                        "symbol": symbol,
                        "broker_conid": conid,
                        "quantity": exec_qty_remaining,
                        "commission": exec_commission_remaining,
                        "source_commission": exec_trade.commission,
                    }
                )
                queue.append(stored_trade)
            else:
                # It's an orphaned closing leg (open leg was before the export period).
                # Reconstruct a closed trade.
                orig_direction = Direction.LONG if exec_trade.direction == Direction.SHORT else Direction.SHORT
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
        exec_qty_remaining = cast(Decimal, exec_trade.quantity)
        exec_commission_remaining = exec_trade.commission
        if exec_commission_remaining is None:
            exec_commission_remaining = Decimal("0")

        # Task 4.4 — Warn when quantity discrepancy may indicate an unregistered split.
        # If the closing execution quantity significantly exceeds what is in the queue,
        # emit a warning so the user knows to check for a missed split event.
        total_open_qty = sum(cast(Decimal, lot.quantity) for lot in queue)
        if exec_trade.pnl is not None and total_open_qty > 0 and exec_qty_remaining > total_open_qty * Decimal("2"):
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
            open_lot_qty = cast(Decimal, open_lot.quantity)
            match_qty = min(open_lot_qty, exec_qty_remaining)

            open_lot_commission = open_lot.commission
            if open_lot_commission is None:
                open_lot_commission = Decimal("0")
            lot_comm = (open_lot_commission * match_qty) / open_lot_qty if open_lot_qty > 0 else Decimal("0")
            exec_comm = (exec_commission_remaining * match_qty) / exec_qty_remaining if exec_qty_remaining > 0 else Decimal("0")

            matched_pnl: Decimal | None = None
            matched_pnl_eur: Decimal | None = None
            matched_net_pnl: Decimal | None = None
            matched_net_pnl_eur: Decimal | None = None
            # The closing execution's price is the exit price for every matched
            # lot in this loop, regardless of whether the broker reported a PnL.
            # It must be bound before the optional `is_closing_leg` block below
            # because the `update` dict always references it.
            exit_price = cast(Decimal, exec_trade.entry_price)
            if is_closing_leg:
                # Exact Gross PnL calculation using entry/exit prices and multiplier.
                # Direction is that of the open lot (the position being closed).
                lot_multiplier = Decimal(open_lot.multiplier)
                open_lot_entry_price = cast(Decimal, open_lot.entry_price)
                if open_lot.direction == Direction.LONG:
                    matched_pnl = (exit_price - open_lot_entry_price) * match_qty * lot_multiplier
                else:
                    matched_pnl = (open_lot_entry_price - exit_price) * match_qty * lot_multiplier
                matched_net_pnl = matched_pnl - (lot_comm + exec_comm)
                exec_trade_pnl_eur = exec_trade.pnl_eur
                exec_trade_pnl = exec_trade.pnl
                if exec_trade_pnl_eur is not None and exec_trade_pnl is not None and exec_trade_pnl != Decimal("0"):
                    # Scale EUR PnL proportionally by the fraction of gross PnL
                    # this match represents.
                    matched_pnl_eur = (exec_trade_pnl_eur * match_qty) / exec_qty_remaining
                    matched_net_pnl_eur = matched_net_pnl * (matched_pnl_eur / matched_pnl) if matched_pnl and matched_pnl != Decimal("0") else matched_net_pnl

            closed_at = exec_trade.opened_at
            if closed_at <= open_lot.opened_at:
                closed_at = open_lot.opened_at + timedelta(seconds=1)

            closed_trade = open_lot.model_copy(
                update={
                    "symbol": symbol,
                    "broker_conid": conid,
                    "quantity": match_qty,
                    "exit_price": exit_price,
                    "closed_at": closed_at,  # actual closing time (or bumped)
                    "commission": lot_comm + exec_comm,
                    "commission_used_open": lot_comm,
                    "commission_used_close": exec_comm,
                    "pnl": matched_pnl,
                    "pnl_eur": matched_pnl_eur,
                    "net_pnl": matched_net_pnl,
                    "net_pnl_eur": matched_net_pnl_eur,
                    # Track the closing execution ID separately so the import
                    # service can link both legs to the trade.
                    "closing_execution_id": exec_trade.source_execution_id,
                }
            )
            closed_trade.source_execution_id = open_lot.source_execution_id
            closed_trade.source_qty_factor = open_lot.source_qty_factor
            closed_trade.source_commission = open_lot.source_commission

            completed_trades.append(closed_trade)

            # Deduct quantities
            exec_qty_remaining -= match_qty
            open_lot.quantity = open_lot_qty - match_qty
            open_lot.commission -= lot_comm
            exec_commission_remaining -= exec_comm

            if open_lot.quantity is not None and open_lot.quantity <= Decimal("0"):
                queue.popleft()

        # If there's still execution quantity remaining, it either flipped the position
        # or it's an orphaned closing quantity.
        if exec_qty_remaining > Decimal("0"):
            if is_closing_leg and not getattr(exec_trade, "is_mixed_execution", False):
                # Orphaned closing remainder
                orig_direction = Direction.LONG if exec_trade.direction == Direction.SHORT else Direction.SHORT
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
                        # PnL is unknown for orphaned lots — entry price is a sentinel.
                        # It will be filled in when matched against a seed_orphaned_lot.
                        "pnl": None,
                        "net_pnl": None,
                        "net_pnl_eur": None,
                    }
                )
                completed_trades.append(orphaned_trade)
            else:
                # Flipped position -> new open lot
                # IMPORTANT: Only carry over source_execution_id if it's not already
                # matched as a closing leg for a preceding match in this same loop.
                # However, for a flip, the exec_trade IS the opening leg of the
                # new lot, so carrying it over is correct.
                flipped_lot = exec_trade.model_copy(
                    update={
                        "symbol": symbol,
                        "broker_conid": conid,
                        "quantity": exec_qty_remaining,
                        "commission": exec_commission_remaining,
                        "pnl": None,
                        "closed_at": None,
                        "exit_price": None,
                        "source_execution_id": exec_trade.source_execution_id,
                        # Reset closing leg info as this is now an open lot
                        "closing_execution_id": None,
                    }
                )
                queue.append(flipped_lot)

    # Apply any trailing corporate actions that occurred after the last execution
    while ca_idx < len(sorted_cas):
        _apply_split_event(open_lots, sorted_cas[ca_idx])
        ca_idx += 1

    # Match any remaining open lots against orphaned lots from future imports
    for key, queue in open_lots.items():
        o_queue = orphaned_lots.get(key)
        while queue and o_queue:
            o_lot = o_queue[0]
            open_lot = queue[0]

            o_lot_qty = cast(Decimal, o_lot.quantity)
            open_lot_qty = cast(Decimal, open_lot.quantity)

            if o_lot.direction != open_lot.direction:
                # Can't match, directions don't align
                break

            match_qty = min(o_lot_qty, open_lot_qty)

            open_lot_commission = open_lot.commission
            if open_lot_commission is None:
                open_lot_commission = Decimal("0")
            o_lot_commission = o_lot.commission
            if o_lot_commission is None:
                o_lot_commission = Decimal("0")
            lot_comm = (open_lot_commission * match_qty) / open_lot_qty if open_lot_qty > 0 else Decimal("0")
            o_lot_comm = (o_lot_commission * match_qty) / o_lot_qty if o_lot_qty > 0 else Decimal("0")

            matched_pnl = None
            matched_pnl_eur = None
            matched_net_pnl = None
            matched_net_pnl_eur = None
            o_exit_price = o_lot.exit_price
            if o_exit_price is not None and o_exit_price > Decimal("0.001"):
                # Exact Gross PnL: use the open lot's true entry price.
                lot_multiplier = Decimal(open_lot.multiplier)
                open_lot_entry_price = cast(Decimal, open_lot.entry_price)
                if open_lot.direction == Direction.LONG:
                    matched_pnl = (o_exit_price - open_lot_entry_price) * match_qty * lot_multiplier
                else:
                    matched_pnl = (open_lot_entry_price - o_exit_price) * match_qty * lot_multiplier
                if matched_pnl is not None:
                    matched_net_pnl = matched_pnl - (lot_comm + o_lot_comm)
            o_lot_pnl_eur = o_lot.pnl_eur
            if o_lot_pnl_eur is not None and o_lot_qty > 0:
                matched_pnl_eur = (o_lot_pnl_eur * match_qty) / o_lot_qty
                if matched_net_pnl is not None:
                    matched_net_pnl_eur = matched_net_pnl * (matched_pnl_eur / matched_pnl) if matched_pnl and matched_pnl != Decimal("0") else matched_net_pnl

            # Create the filled orphaned lot by taking the
            # exit details from the orphaned lot
            # and the entry details from the open lot
            filled_orphaned_trade = o_lot.model_copy(
                update={
                    "quantity": match_qty,
                    "entry_price": open_lot.entry_price,
                    "opened_at": open_lot.opened_at,
                    "commission": lot_comm + o_lot_comm,
                    "pnl": matched_pnl,
                    "pnl_eur": matched_pnl_eur,
                    "net_pnl": matched_net_pnl,
                    "net_pnl_eur": matched_net_pnl_eur,
                }
            )
            completed_trades.append(filled_orphaned_trade)

            # Deduct
            open_lot.quantity = open_lot_qty - match_qty
            open_lot.commission -= lot_comm
            o_lot.quantity = o_lot_qty - match_qty
            o_lot.commission -= o_lot_comm

            if open_lot.quantity is not None and open_lot.quantity <= Decimal("0"):
                queue.popleft()
            if o_lot.quantity is not None and o_lot.quantity <= Decimal("0"):
                o_queue.popleft()

    # Add any remaining open lots to the output
    for queue in open_lots.values():
        for lot in queue:
            # Ensure it looks like an open trade
            lot.exit_price = None
            lot.closed_at = None
            lot.pnl = None
            lot.net_pnl = None
            lot.pnl_eur = None
            lot.net_pnl_eur = None
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
    keys_to_remap: list[tuple[tuple[str, str | None, str], tuple[str, str | None, str]]] = []

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

        # Adjust all lots in this queue
        for lot in queue:
            # Task 4.4 — IMPORTANT: Use the ratio provided in the corporate action
            # to adjust quantities and prices.
            # However, we must ensure we don't double-adjust a lot if multiple
            # CorporateActions are applied in the same day (rare but possible).
            # The aggregator loop handles this by applying CAs in sequence
            # before each execution.

            # Use a threshold check to see if this CA was already applied to this lot.
            # Each CA has a unique date/ratio/symbol.
            # We can use the lot's metadata or just trust the sequential processing.
            # Wait — if ca.ratio is 1.0, it's a no-op.
            if ca.ratio == Decimal("1"):
                continue

            lot_qty = cast(Decimal, lot.quantity)
            lot_entry_price = cast(Decimal, lot.entry_price)
            lot.quantity = lot_qty * ca.ratio
            lot.entry_price = lot_entry_price / ca.ratio
            lot.source_qty_factor = (lot.source_qty_factor or Decimal("1")) * ca.ratio
            # Update the conid stored in each lot to the new conid (if provided)
            if ca.new_conid is not None:
                lot.broker_conid = ca.new_conid

            # Scale source_commission proportionally if it was set
            if lot.source_commission is not None:
                lot.source_commission = lot.source_commission * ca.ratio

            # Note: We do NOT scale commission_used_open here because it's only
            # set when a lot is matched and moved to completed_trades.
            # Open lots only have 'commission'.
            if lot.commission is not None:
                lot.commission = lot.commission * ca.ratio

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
                "Conid remap collision: merging queues for old_key=%s into new_key=%s. This may indicate duplicate corporate actions.",
                old_key,
                new_key,
            )
        else:
            open_lots[new_key] = existing_queue
        logger.debug("Re-keyed open lots queue from %s → %s.", old_key, new_key)


def aggregate_executions_fifo_with_sources(
    executions: list[TradeCreate],
    symbol_map: dict[str, str] | None = None,
    conid_map: dict[str, str] | None = None,
    corporate_actions: Sequence[CorporateActionLike] | None = None,
    seed_open_lots: Sequence[SeedLotLike] | None = None,
    seed_orphaned_lots: Sequence[SeedLotLike] | None = None,
) -> list[TradeCreateWithSources]:
    """Enhanced aggregation that tracks source executions for split-aware linking.

    This function wraps the existing aggregate_executions_fifo() and analyzes
    which source executions contributed to each trade to enable split detection.

    Split Detection Logic:
    - An execution needs splitting when it contributes to MULTIPLE trades
    - This happens when a large entry/exit execution is matched against
      multiple smaller counter-executions in FIFO order

    Args:
        Same as aggregate_executions_fifo().

    Returns:
        List of TradeCreateWithSources objects that track which executions
        contributed to each aggregated trade, with proper allocation tracking.
    """
    # Call the existing aggregation function
    aggregated_trades = aggregate_executions_fifo(
        executions=executions,
        symbol_map=symbol_map,
        conid_map=conid_map,
        corporate_actions=corporate_actions,
        seed_open_lots=seed_open_lots,
        seed_orphaned_lots=seed_orphaned_lots,
    )

    # Create TradeCreateWithSources wrappers with proper allocation tracking.
    # Each closed trade contributes two allocations: one for the opening execution
    # and one for the closing execution.  Open (unclosed) trades contribute only
    # the opening execution allocation.
    trades_with_sources: list[TradeCreateWithSources] = []

    for trade in aggregated_trades:
        source_allocations: list[ExecutionAllocation] = []
        quantity_for_this_trade = trade.quantity or Decimal("0")

        # Track seen execution IDs for this trade to prevent double-counting
        # within a single trade (e.g. flips).
        seen_execution_ids: set[uuid.UUID | str] = set()

        if trade.source_execution_id:
            # Scale opening quantity proportionally if it was adjusted by splits.
            # (trade.quantity is the matched quantity after split adjustments,
            # but we need the portion of the ORIGINAL execution used).
            source_qty_factor = trade.source_qty_factor or Decimal("1")
            allocated_qty = quantity_for_this_trade / source_qty_factor

            # Calculate the portion of commission to allocate.
            # We use the original source_commission if available.
            source_comm = trade.source_commission
            if source_comm is None:
                c = trade.commission
                source_comm = c / Decimal("2") if c else Decimal("0")

            # Scale commission proportionally to the matched quantity
            # relative to the total quantity in the open lot before matching.
            # (In FIFO, a large entry might be split across multiple exits).
            # We don't have the original lot quantity here easily, so we
            # use a simplified approach for now: the aggregator already
            # calculates lot_comm (commission portion for the match).
            # Let's use that.

            source_allocations.append(
                ExecutionAllocation(
                    execution_id=trade.source_execution_id,
                    quantity_used=allocated_qty,
                    commission_used=trade.commission_used_open or Decimal("0"),
                    entry_price=trade.entry_price or Decimal("0"),
                )
            )
            seen_execution_ids.add(trade.source_execution_id)

        # Only add closing allocation if it's different from the source allocation.
        # This prevents double-counting when source_execution_id == closing_id,
        # which can happen for single-execution round-trips
        # (e.g. IBKR reported PnL on a flip).
        if trade.closing_execution_id:
            # For closing executions, the split factor is already applied
            # to the execution quantity before it enters the aggregator, so we
            # don't need to divide by source_qty_factor here.

            # CRITICAL: Verify if this closing execution was already used as the
            # opening leg for the SAME trade (happens in position flips).
            if trade.closing_execution_id in seen_execution_ids:
                # Deduplicate within the same trade: the same execution ID appearing
                # as both opening and closing leg (e.g. position flips) must only
                # be counted once to avoid "Allocation overflow" during validation.
                pass
            else:
                source_allocations.append(
                    ExecutionAllocation(
                        execution_id=trade.closing_execution_id,
                        quantity_used=quantity_for_this_trade,
                        commission_used=trade.commission_used_close or Decimal("0"),
                        entry_price=trade.exit_price or Decimal("0"),
                    )
                )
                seen_execution_ids.add(trade.closing_execution_id)

        trade_with_sources = TradeCreateWithSources(
            trade_create=trade,
            source_executions=source_allocations,
        )
        logger.debug(
            "Trade with sources: symbol=%s, qty=%s, sources=%s",
            trade.symbol,
            quantity_for_this_trade,
            [f"{a.execution_id}:{a.quantity_used}" for a in source_allocations],
        )
        trades_with_sources.append(trade_with_sources)

    # Build usage counts per execution for split detection in O(n).
    # Both opening (source_execution_id) and closing (closing_execution_id)
    # executions are tracked so splits on either leg are detected correctly.
    execution_usage_count: dict[uuid.UUID | str, int] = {}

    for trade_source in trades_with_sources:
        for allocation in trade_source.source_executions:
            exec_id = allocation.execution_id
            execution_usage_count[exec_id] = execution_usage_count.get(exec_id, 0) + 1

    # Log split detection summary
    executions_needing_split = {exec_id for exec_id, usage_count in execution_usage_count.items() if usage_count > 1}

    if executions_needing_split:
        logger.info(
            "Split detection: %d executions will be split across multiple trades",
            len(executions_needing_split),
        )
        for exec_id in executions_needing_split:
            logger.debug(
                "Execution %s used by %d trades",
                exec_id,
                execution_usage_count[exec_id],
            )

    return trades_with_sources
