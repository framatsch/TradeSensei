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
from app.schemas.tax import AccountTaxSummary, TaxAnnualSummary, TaxCategoryBlock

_ZERO = Decimal("0")

_EQUITY_CATEGORY = "Aktie (§20 Abs. 2 Nr. 1 EStG)"
_DERIVATIVE_CATEGORY = "Derivat (§20 Abs. 2 Nr. 3 EStG)"

_TRADE_CSV_HEADERS = [
    "Konto",
    "Symbol",
    "Asset-Klasse",
    "Kategorie",
    "Eröffnungsdatum",
    "Schließungsdatum",
    "P&L (USD)",
    "EUR/USD-Kurs",
    "P&L (EUR)",
]

_CASH_CSV_HEADERS = [
    "Konto",
    "Datum",
    "Typ",
    "Symbol",
    "Betrag (Originalwährung)",
    "Währung",
    "Betrag (EUR)",
    "Beschreibung",
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
        Also fetches dividend, withholding-tax and interest cash transactions
        and populates the corresponding totals.

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

        cash_rows = await self._repo.get_cash_flow_rows(
            self._session,
            year=year,
            user_id=user_id,
        )
        # Build lookup: account_id -> (dividends, withholding, interest)
        cash_by_account: dict[uuid.UUID | None, tuple[Decimal, Decimal, Decimal]] = {
            row[0]: (row[1], row[2], row[3]) for row in cash_rows
        }

        overall_equities_gains = _ZERO
        overall_equities_losses = _ZERO
        overall_equities_count = 0
        overall_derivatives_gains = _ZERO
        overall_derivatives_losses = _ZERO
        overall_derivatives_count = 0
        overall_total_missing = 0
        overall_dividends = _ZERO
        overall_withholding = _ZERO
        overall_interest = _ZERO

        # Group rows by account
        account_groups: dict[
            uuid.UUID | None,
            list[tuple[uuid.UUID | None, str | None, bool, Decimal, Decimal, int, int]],
        ] = {}
        for row in rows:
            acc_id = row[0]
            if acc_id not in account_groups:
                account_groups[acc_id] = []
            account_groups[acc_id].append(row)

        # Also include accounts that have cash transactions but no trades
        for acc_id in cash_by_account:
            if acc_id not in account_groups:
                account_groups[acc_id] = []

        account_summaries: list[AccountTaxSummary] = []

        for acc_id, acc_rows in account_groups.items():
            # Determine account name from trade rows (or leave None)
            acc_name: str | None = acc_rows[0][1] if acc_rows else None

            acc_equities_gains = _ZERO
            acc_equities_losses = _ZERO
            acc_equities_count = 0
            acc_derivatives_gains = _ZERO
            acc_derivatives_losses = _ZERO
            acc_derivatives_count = 0
            acc_total_missing = 0

            for (
                _,
                _,
                is_equity,
                gains_eur,
                losses_eur,
                trade_count,
                missing_count,
            ) in acc_rows:
                acc_total_missing += missing_count
                overall_total_missing += missing_count

                if is_equity:
                    acc_equities_gains = Decimal(str(gains_eur))
                    acc_equities_losses = Decimal(str(losses_eur))
                    acc_equities_count = int(trade_count)

                    overall_equities_gains += acc_equities_gains
                    overall_equities_losses += acc_equities_losses
                    overall_equities_count += acc_equities_count
                else:
                    acc_derivatives_gains = Decimal(str(gains_eur))
                    acc_derivatives_losses = Decimal(str(losses_eur))
                    acc_derivatives_count = int(trade_count)

                    overall_derivatives_gains += acc_derivatives_gains
                    overall_derivatives_losses += acc_derivatives_losses
                    overall_derivatives_count += acc_derivatives_count

            # Cash flow totals for this account
            dividends, withholding, interest = cash_by_account.get(
                acc_id, (_ZERO, _ZERO, _ZERO)
            )
            overall_dividends += dividends
            overall_withholding += withholding
            overall_interest += interest

            acc_equities_net = acc_equities_gains + acc_equities_losses
            acc_derivatives_net = acc_derivatives_gains + acc_derivatives_losses

            account_summaries.append(
                AccountTaxSummary(
                    account_id=acc_id,
                    account_name=acc_name,
                    equities=TaxCategoryBlock(
                        gains_eur=acc_equities_gains,
                        losses_eur=acc_equities_losses,
                        net_eur=acc_equities_net,
                        trade_count=acc_equities_count,
                    ),
                    derivatives=TaxCategoryBlock(
                        gains_eur=acc_derivatives_gains,
                        losses_eur=acc_derivatives_losses,
                        net_eur=acc_derivatives_net,
                        trade_count=acc_derivatives_count,
                    ),
                    total_net_eur=acc_equities_net + acc_derivatives_net,
                    trades_missing_eur=acc_total_missing,
                    dividends_eur=dividends,
                    withholding_tax_eur=withholding,
                    interest_eur=interest,
                )
            )

        overall_equities_net = overall_equities_gains + overall_equities_losses
        overall_derivatives_net = overall_derivatives_gains + overall_derivatives_losses

        return TaxAnnualSummary(
            year=year,
            equities=TaxCategoryBlock(
                gains_eur=overall_equities_gains,
                losses_eur=overall_equities_losses,
                net_eur=overall_equities_net,
                trade_count=overall_equities_count,
            ),
            derivatives=TaxCategoryBlock(
                gains_eur=overall_derivatives_gains,
                losses_eur=overall_derivatives_losses,
                net_eur=overall_derivatives_net,
                trade_count=overall_derivatives_count,
            ),
            total_net_eur=overall_equities_net + overall_derivatives_net,
            trades_missing_eur=overall_total_missing,
            dividends_eur=overall_dividends,
            withholding_tax_eur=overall_withholding,
            interest_eur=overall_interest,
            accounts=account_summaries,
        )

    async def get_annual_csv(
        self,
        year: int,
        user_id: uuid.UUID,
    ) -> str:
        """Build the Anlage KAP CSV for a given year and user.

        The CSV contains two sections:
        1. **Trades** — closed trades with P&L in EUR (one row per trade).
        2. **Kapitalerträge** — dividend, withholding-tax and interest cash
           transactions for the year (one row per cash transaction).

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
        cash_txs = await self._repo.get_annual_cash_transactions(
            self._session,
            year=year,
            user_id=user_id,
        )

        output = io.StringIO()
        writer = csv.writer(output, dialect="excel")

        # ── Section 1: Trades ──────────────────────────────────────────────────
        writer.writerow(["## Trades (§20 Abs. 2 EStG)"])
        writer.writerow(_TRADE_CSV_HEADERS)

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

            account_name = trade.account.name if trade.account else ""

            writer.writerow(
                [
                    account_name,
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

        # ── Section 2: Kapitalerträge (Dividenden, Quellensteuer, Zinsen) ──────
        writer.writerow([])
        writer.writerow(["## Kapitalerträge (§20 Abs. 1 EStG)"])
        writer.writerow(_CASH_CSV_HEADERS)

        for ct in cash_txs:
            account_name = ct.account.name if ct.account else ""
            writer.writerow(
                [
                    account_name,
                    ct.date.strftime("%Y-%m-%d"),
                    str(ct.type),
                    ct.symbol or "",
                    str(ct.amount),
                    ct.currency,
                    str(ct.amount_eur) if ct.amount_eur is not None else "",
                    ct.description or "",
                ]
            )

        # UTF-8 BOM for Excel compatibility.
        return "\ufeff" + output.getvalue()
