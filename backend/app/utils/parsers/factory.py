"""Broker parser factory.

Maps :class:`BrokerType` enum values to concrete
:class:`~app.utils.parsers.base.BrokerParser` instances.
"""

from enum import StrEnum

from app.core.exceptions import UnsupportedBrokerError
from app.utils.parsers.base import BrokerParser
from app.utils.parsers.ibkr_xml import IBKRXMLParser
from app.utils.parsers.schwab import SchwabParser


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
        BrokerType.SCHWAB: SchwabParser(),
    }
    parser = parsers.get(broker)
    if parser is None:
        raise UnsupportedBrokerError(
            f"No parser available for broker {broker!r}. "
            f"Supported brokers: {', '.join(BrokerType)}."
        )
    return parser
