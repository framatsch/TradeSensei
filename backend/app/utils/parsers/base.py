"""Abstract base class for broker file parsers."""

from abc import ABC, abstractmethod

from app.schemas.trade import TradeCreate


class BrokerParser(ABC):
    """Abstract base class for broker file parsers.

    Concrete subclasses implement :meth:`parse` for a specific broker's
    export format.  All parsers operate on raw bytes and return validated
    :class:`~app.schemas.trade.TradeCreate` instances; they have no
    side effects and no dependencies on the database or HTTP layer.
    """

    @abstractmethod
    def parse(self, content: bytes, filename: str) -> list[TradeCreate]:
        """Parse broker export file content into a list of TradeCreate schemas.

        Args:
            content: Raw file bytes.
            filename: Original filename (used to detect CSV vs XLSX).

        Returns:
            List of :class:`~app.schemas.trade.TradeCreate` instances
            ready for import.

        Raises:
            ImportParseError: If the file cannot be parsed or has an
                unrecognised format.
        """
