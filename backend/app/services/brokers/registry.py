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

"""Broker adapter registry — the single source of truth for broker dispatch.

Adding a broker means adding one adapter package and one entry in
:data:`_ADAPTERS`; route handlers, ``ImportService`` and ``BrokerService``
pick it up without changes.
"""

from app.core.exceptions import UnsupportedBrokerError
from app.models.account import AccountType
from app.services.brokers.contracts import BrokerAdapter, BrokerType
from app.services.brokers.ibkr.adapter import IBKR_ADAPTER
from app.services.brokers.schwab.adapter import SCHWAB_ADAPTER

_ADAPTERS: tuple[BrokerAdapter, ...] = (IBKR_ADAPTER, SCHWAB_ADAPTER)

_BY_KEY: dict[BrokerType, BrokerAdapter] = {adapter.key: adapter for adapter in _ADAPTERS}
_BY_ACCOUNT_TYPE: dict[AccountType, BrokerAdapter] = {adapter.account_type: adapter for adapter in _ADAPTERS}

if len(_BY_KEY) != len(_ADAPTERS) or len(_BY_ACCOUNT_TYPE) != len(_ADAPTERS):
    raise RuntimeError("Broker adapters must have unique keys and account types.")


def get_adapter(key: BrokerType) -> BrokerAdapter:
    """Return the adapter registered for ``key``.

    Raises:
        UnsupportedBrokerError: If no adapter is registered for ``key``.
    """
    adapter = _BY_KEY.get(key)
    if adapter is None:
        raise UnsupportedBrokerError(f"No parser available for broker {key!r}. Supported brokers: {', '.join(BrokerType)}.")
    return adapter


def adapter_for_account_type(account_type: AccountType) -> BrokerAdapter | None:
    """Return the adapter serving ``account_type``, or ``None`` (e.g. ``MANUAL``)."""
    return _BY_ACCOUNT_TYPE.get(account_type)


def registered_adapters() -> tuple[BrokerAdapter, ...]:
    """Return all registered adapters in registration order."""
    return _ADAPTERS
