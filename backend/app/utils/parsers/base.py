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

"""Abstract base class for broker file parsers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.broker_raw_transaction import BrokerRawTransactionCreate
from app.schemas.corporate_action import CorporateActionCreateRequest
from app.schemas.trade import TradeCreate
from app.utils.parsers.aggregator import CorporateActionLike, SeedLotLike


class BrokerParser(ABC):
    """Abstract base class for broker file parsers.

    Concrete subclasses implement :meth:`parse` for a specific broker's
    export format.  All parsers operate on raw bytes and return validated
    :class:`~app.schemas.trade.TradeCreate` instances.
    They have no side effects and no dependencies on the database or HTTP layer.

    Optionally, subclasses may override :meth:`enrich_pnl_eur` to perform
    asynchronous post-parse enrichment (e.g. fetching FX rates) before
    trades are persisted.

    Subclasses that support the raw-data layer should override
    :meth:`parse_raw` to return
    :class:`~app.schemas.broker_raw_transaction.BrokerRawTransactionCreate`
    records instead of aggregated :class:`~app.schemas.trade.TradeCreate`
    records.
    """

    @abstractmethod
    def parse(
        self,
        content: bytes,
        filename: str,
        corporate_actions: Sequence[CorporateActionLike] | None = None,
        seed_open_lots: Sequence[SeedLotLike] | None = None,
        seed_orphaned_lots: Sequence[SeedLotLike] | None = None,
    ) -> tuple[list[TradeCreate], list[object]]:
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
                - Ignored second element (reserved for backward compatibility)

        Raises:
            ImportParseError: If the file cannot be parsed or has an
                unrecognised format.
        """

    def parse_raw(
        self,
        content: bytes,
        filename: str,
    ) -> tuple[
        list[BrokerRawTransactionCreate],
        list[CorporateActionCreateRequest],
    ]:
        """Parse broker export file content into raw transaction records.

        Returns one
        :class:`~app.schemas.broker_raw_transaction.BrokerRawTransactionCreate`
        per broker execution — no FIFO aggregation is performed.  The caller
        is responsible for translating these into
        :class:`~app.models.logical_execution.LogicalExecution`
        records and subsequently running aggregation.

        The default implementation raises :exc:`NotImplementedError`.  Parsers
        that support the raw-data layer override this method.

        Args:
            content: Raw file bytes.
            filename: Original filename (used to detect CSV vs XLSX).

        Returns:
            A tuple of:
            - List of
              :class:`~app.schemas.broker_raw_transaction.BrokerRawTransactionCreate`
            - List of :class:`~app.schemas.corporate_action.CorporateActionCreateRequest`

        Raises:
            NotImplementedError: If the parser has not implemented raw parsing.
            ImportParseError: If the file cannot be parsed.
        """
        raise NotImplementedError(f"{type(self).__name__} does not implement parse_raw().")

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
