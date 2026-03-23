"""Abstract base class for broker file parsers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.cash_transaction import CashTransactionCreateRequest
from app.schemas.trade import TradeCreate
from app.utils.parsers.aggregator import CorporateActionLike, SeedLotLike


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
        self,
        content: bytes,
        filename: str,
        corporate_actions: Sequence[CorporateActionLike] | None = None,
        seed_open_lots: Sequence[SeedLotLike] | None = None,
    ) -> tuple[list[TradeCreate], list[CashTransactionCreateRequest]]:
        """Parse broker export file content into Pydantic schemas.

        Args:
            content: Raw file bytes.
            filename: Original filename (used to detect CSV vs XLSX).
            corporate_actions: Optional sequence of corporate actions to pass to
                the aggregator so that split adjustments are applied during
                execution matching.  When ``None`` the behaviour is unchanged
                from before.
            seed_open_lots: Optional sequence of existing open DB trades to
                pre-populate the FIFO aggregator queue.  When provided,
                incoming closing executions are matched against these seed lots
                first, allowing cross-period imports to correctly close
                positions opened in a prior import.  Closed results originating
                from a seed lot carry ``db_trade_id`` so the caller can issue an
                UPDATE rather than an INSERT.

        Returns:
            A tuple containing:
                - List of :class:`~app.schemas.trade.TradeCreate` instances
                - List of cash transaction creation requests

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
        return
