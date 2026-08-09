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

"""Helpers for split-adjusted execution and trade values.

All split-aware paths use the same arithmetic and effective-date boundary:

- ``quantity *= ratio``
- ``price /= ratio``

Execution date comparisons are done on the exchange-local calendar date.
Until instrument exchange metadata is available on execution rows, USD
instruments default to ``America/New_York``.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.models.corporate_action import CorporateAction


def split_adjust_execution_values(
    raw_price: Decimal,
    raw_quantity: Decimal,
    executed_at: datetime,
    symbol: str,
    conid: str | None,
    corporate_actions: Sequence[CorporateAction],
    currency: str | None = None,
) -> tuple[Decimal, Decimal]:
    """Return split-adjusted execution values for chart alignment.

    Applies every matching corporate action in chronological order using
    ``Decimal`` arithmetic.
    """
    executed_local_date = execution_effective_date(
        executed_at=executed_at,
        currency=currency,
    )

    applicable_actions = [
        action for action in corporate_actions if _matches_action(action=action, symbol=symbol, conid=conid) and action.date > executed_local_date
    ]
    if not applicable_actions:
        return raw_price, raw_quantity

    return apply_split_actions(raw_price, raw_quantity, applicable_actions)


def split_adjust_execution_values_for_holding_period(
    raw_price: Decimal,
    raw_quantity: Decimal,
    executed_at: datetime,
    trade_opened_at: datetime,
    trade_closed_at: datetime | None,
    symbol: str,
    conid: str | None,
    corporate_actions: Sequence[CorporateAction],
    currency: str | None = None,
) -> tuple[Decimal, Decimal]:
    """Return split-adjusted execution values using the holding-period rule.

    This is used for persisted trade values. A split applies only when the
    position was open across the effective date, and only to pre-split legs.
    """
    opened_local_date = execution_effective_date(
        executed_at=trade_opened_at,
        currency=currency,
    )
    closed_local_date = execution_effective_date(executed_at=trade_closed_at, currency=currency) if trade_closed_at is not None else None
    executed_local_date = execution_effective_date(
        executed_at=executed_at,
        currency=currency,
    )

    applicable_actions = [
        action
        for action in corporate_actions
        if _matches_action(action=action, symbol=symbol, conid=conid)
        and opened_local_date < action.date
        and (closed_local_date is None or closed_local_date >= action.date)
        and action.date > executed_local_date
    ]
    if not applicable_actions:
        return raw_price, raw_quantity

    return apply_split_actions(raw_price, raw_quantity, applicable_actions)


def apply_split_ratio(
    raw_price: Decimal,
    raw_quantity: Decimal,
    ratio: Decimal,
) -> tuple[Decimal, Decimal]:
    """Apply one split ratio to price/quantity."""
    if ratio == Decimal("1"):
        return raw_price, raw_quantity
    return raw_price / ratio, raw_quantity * ratio


def apply_split_actions(
    raw_price: Decimal,
    raw_quantity: Decimal,
    corporate_actions: Sequence[CorporateAction],
) -> tuple[Decimal, Decimal]:
    """Apply multiple actions in chronological order."""
    price = raw_price
    quantity = raw_quantity
    for action in sorted(corporate_actions, key=lambda item: item.date):
        price, quantity = apply_split_ratio(price, quantity, action.ratio)
    return price, quantity


def resolve_instrument_timezone(currency: str | None) -> ZoneInfo:
    """Resolve instrument timezone for effective-date comparisons.

    USD instruments default to America/New_York until exchange metadata is
    available on execution rows.
    """
    if currency == "USD":
        return ZoneInfo("America/New_York")
    return ZoneInfo("UTC")


def execution_effective_date(executed_at: datetime, currency: str | None) -> date:
    """Return the exchange-local effective date for one execution timestamp."""
    return executed_at.astimezone(resolve_instrument_timezone(currency)).date()


def _matches_action(
    action: CorporateAction,
    symbol: str,
    conid: str | None,
) -> bool:
    """Check whether a corporate action applies to one execution leg."""
    if action.symbol == symbol:
        return True

    if conid is None:
        return False

    return conid in {action.old_conid, action.new_conid}
