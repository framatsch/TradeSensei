"""Business-logic service for annual tax summary reporting.

This layer orchestrates :class:`~app.repositories.tax_repository.TaxRepository`
and assembles the :class:`~app.schemas.tax.TaxAnnualSummary` DTO for the
``GET /tax/annual-summary`` endpoint.

No SQLAlchemy queries are issued here — all data access is delegated to the
repository layer.  No HTTP concepts (``Request``, ``Response``, status codes)
appear here.
"""

import csv
import io
import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trade import AssetClass
from app.repositories.tax_repository import TaxRepository
from app.schemas.tax import TaxAnnualSummary, TaxCategoryBlock

_ZERO = Decimal("0")

_EQUITY_CATEGORY = "Aktie (§20 Abs. 2 Nr. 1 EStG)"
_DERIVATIVE_CATEGORY = "Derivat (§20 Abs. 2 Nr. 3 EStG)"

_CSV_HEADERS = [
    "Symbol",
    "Asset-Klasse",
    "Kategorie",
    "Eröffnungsdatum",
    "Schließungsdatum",
    "P&L (USD)",
    "EUR/USD-Kurs",
    "P&L (EUR)",
]


class TaxService:
    """Service layer for computing annual tax summaries (§20 EStG).

    Fetches aggregate P&L data from the repository, applies the German
    §20 EStG categorisation rules, and assembles the final DTO.

    Args:
        session: An open :class:`AsyncSession` managed by the caller.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with a database session.

        Args:
            session: The session to use for all data-access calls within
                this request lifecycle.
        """
        self._repo = TaxRepository()
        self._session = session

    async def get_annual_summary(
        self,
        year: int,
        user_id: uuid.UUID,
    ) -> TaxAnnualSummary:
        """Compute the annual tax summary for a given year and user.

        Fetches closed trades with ``pnl_eur IS NOT NULL`` (plus trades where
        ``pnl_eur`` is NULL for the ``trades_missing_eur`` counter), then
        groups them into the §20 EStG categories and computes totals.

        Args:
            year: Calendar year to summarise.
            user_id: UUID of the authenticated user.

        Returns:
            A fully populated :class:`~app.schemas.tax.TaxAnnualSummary`.
        """
        rows = await self._repo.get_annual_summary_rows(
            self._session,
            year=year,
            user_id=user_id,
        )

        equities_gains = _ZERO
        equities_losses = _ZERO
        equities_count = 0
        derivatives_gains = _ZERO
        derivatives_losses = _ZERO
        derivatives_count = 0
        total_missing = 0

        for is_equity, gains_eur, losses_eur, trade_count, missing_count in rows:
            total_missing += missing_count
            if is_equity:
                equities_gains = Decimal(str(gains_eur))
                equities_losses = Decimal(str(losses_eur))
                equities_count = int(trade_count)
            else:
                derivatives_gains = Decimal(str(gains_eur))
                derivatives_losses = Decimal(str(losses_eur))
                derivatives_count = int(trade_count)

        equities_net = equities_gains + equities_losses
        derivatives_net = derivatives_gains + derivatives_losses

        return TaxAnnualSummary(
            year=year,
            equities=TaxCategoryBlock(
                gains_eur=equities_gains,
                losses_eur=equities_losses,
                net_eur=equities_net,
                trade_count=equities_count,
            ),
            derivatives=TaxCategoryBlock(
                gains_eur=derivatives_gains,
                losses_eur=derivatives_losses,
                net_eur=derivatives_net,
                trade_count=derivatives_count,
            ),
            total_net_eur=equities_net + derivatives_net,
            trades_missing_eur=total_missing,
        )

    async def get_annual_csv(
        self,
        year: int,
        user_id: uuid.UUID,
    ) -> str:
        """Build the Anlage KAP CSV for a given year and user.

        Fetches individual closed trades with ``pnl_eur`` set (or NULL),
        computes an implied EUR/USD rate where possible, and writes one
        CSV row per trade sorted by ``closed_at`` ascending.

        Args:
            year: Calendar year to export.
            user_id: UUID of the authenticated user.

        Returns:
            The complete CSV content as a UTF-8 string (with BOM for
            Excel compatibility).
        """
        trades = await self._repo.get_annual_trades(
            self._session,
            year=year,
            user_id=user_id,
        )

        output = io.StringIO()
        writer = csv.writer(output, dialect="excel")
        writer.writerow(_CSV_HEADERS)

        for trade in trades:
            is_equity = trade.asset_class == AssetClass.EQUITY
            category = _EQUITY_CATEGORY if is_equity else _DERIVATIVE_CATEGORY

            # Compute implied EUR/USD rate if both pnl and pnl_eur are set.
            fx_rate: str
            if (
                trade.pnl is not None
                and trade.pnl_eur is not None
                and trade.pnl_eur != _ZERO
            ):
                implied = Decimal(str(trade.pnl)) / Decimal(str(trade.pnl_eur))
                fx_rate = str(implied.quantize(Decimal("0.00000001")))
            else:
                fx_rate = ""

            writer.writerow(
                [
                    trade.symbol,
                    str(trade.asset_class),
                    category,
                    (trade.opened_at.strftime("%Y-%m-%d") if trade.opened_at else ""),
                    (trade.closed_at.strftime("%Y-%m-%d") if trade.closed_at else ""),
                    str(trade.pnl) if trade.pnl is not None else "",
                    fx_rate,
                    str(trade.pnl_eur) if trade.pnl_eur is not None else "",
                ]
            )

        # UTF-8 BOM for Excel compatibility.
        return "\ufeff" + output.getvalue()
