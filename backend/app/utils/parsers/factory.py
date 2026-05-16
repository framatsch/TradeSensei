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

"""Broker parser factory.

Maps :class:`BrokerType` enum values to concrete
:class:`~app.utils.parsers.base.BrokerParser` instances.
"""

from enum import StrEnum

from app.core.exceptions import UnsupportedBrokerError
from app.utils.parsers.base import BrokerParser
from app.utils.parsers.ibkr_xml import IBKRXMLParser
from app.utils.parsers.schwab_json import SchwabJSONParser


class BrokerType(StrEnum):
    """Supported broker identifiers for file import."""

    IBKR = "ibkr"
    SCHWAB = "schwab"


def get_parser(broker: BrokerType) -> BrokerParser:
    """Return the concrete parser for the given broker type.

    Args:
        broker: The broker to retrieve a parser for.

    Returns:
        A :class:`~app.utils.parsers.base.BrokerParser` instance.

    Raises:
        UnsupportedBrokerError: If no parser is registered for the
            supplied ``broker`` value.
    """
    parsers: dict[BrokerType, BrokerParser] = {
        BrokerType.IBKR: IBKRXMLParser(),
        BrokerType.SCHWAB: SchwabJSONParser(),
    }
    parser = parsers.get(broker)
    if parser is None:
        raise UnsupportedBrokerError(f"No parser available for broker {broker!r}. Supported brokers: {', '.join(BrokerType)}.")
    return parser
