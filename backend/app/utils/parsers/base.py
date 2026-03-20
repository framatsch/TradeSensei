"""Abstract base class for broker file parsers."""

from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.cash_transaction import CashTransactionCreateRequest
from app.schemas.trade import TradeCreate


class BrokerParser(ABC):
    """Abstract base class for broker file parsers.

    Concrete subclasses implement :meth:`parse` for a specific broker's
    export format.  All parsers operate on raw bytes and return validated
    :class:`~app.schemas.trade.TradeCreate` and
    :class:`~app.schemas.cash_transaction.CashTransactionCreateRequest` instances.
    They have no side effects and no dependencies on the database or HTTP layer.

    Optionally, subclasses may override :meth:`enrich_pnl_eur` to perform
    asynchronous post-parse enrichment (e.g. fetching FX rates) before
    trades are persisted.
    """

    @abstractmethod
    def parse(
        self, content: bytes, filename: str
    ) -> tuple[list[TradeCreate], list[CashTransactionCreateRequest]]:
        """Parse broker export file content into TradeCreate and CashTransactionCreateRequest schemas.

        Args:
            content: Raw file bytes.
            filename: Original filename (used to detect CSV vs XLSX).

        Returns:
            A tuple containing:
                - List of :class:`~app.schemas.trade.TradeCreate` instances
                - List of :class:`~app.schemas.cash_transaction.CashTransactionCreateRequest` instances

        Raises:
            ImportParseError: If the file cannot be parsed or has an
                unrecognised format.
        """

    async def enrich_pnl_eur(
        self,
        trades: list[TradeCreate],
        session: AsyncSession,
    ) -> None:
        """Enrich trades with EUR-converted P&L values (no-op by default).

        Subclasses that support EUR enrichment override this method to
        look up the applicable USD→EUR exchange rate and set
        ``pnl_eur`` (and ``currency``) on each trade in-place.

        Args:
            trades: Parsed trades to enrich.  Modified in-place via
                ``model_copy``.
            session: Active async DB session for FX-rate lookups.
        """
