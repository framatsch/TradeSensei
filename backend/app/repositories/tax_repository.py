"""Async repository for tax-related aggregate queries.

Provides the raw SQL aggregation needed by :class:`~app.services.tax_service.TaxService`
to build the annual tax summary.  No business logic or categorisation lives here.
"""

import uuid
from decimal import Decimal

from sqlalchemy import and_, case, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.account import Account
from app.models.cash_transaction import CashTransaction, CashTransactionType
from app.models.trade import (  # noqa: F401 (AssetClass used in case expr)
    AssetClass,
    Trade,
)


class TaxRepository:
    """Data-access layer for annual tax summary queries.

    All methods are scoped to a single user and perform only read operations.
    """

    async def get_annual_summary_rows(
        self,
        session: AsyncSession,
        year: int,
        user_id: uuid.UUID,
    ) -> list[tuple[uuid.UUID | None, str | None, bool, Decimal, Decimal, int, int]]:
        """Aggregate closed trades with pnl_eur for a given year and user.

        Groups by ``Account.id``, ``Account.name``, and ``is_equity`` (True for
        :attr:`~app.models.trade.AssetClass.EQUITY`, False for all others) and returns
        aggregated gains, losses, trade count, and count of trades with a NULL
        ``pnl_eur``.

        Only trades where ``pnl IS NOT NULL`` (closed trades) are included.
        ``pnl_eur`` is used when available; if NULL (Bundesbank FX lookup failed
        at import time), ``pnl`` (original-currency amount) is used as a fallback
        so that trade P&L is never silently omitted.  ``trades_missing_eur``
        counts trades that fell back to the original-currency amount.

        Args:
            session: Active async SQLAlchemy session.
            year: Calendar year to filter on (based on ``closed_at``).
            user_id: UUID of the authenticated user.

        Returns:
            A list of 7-tuples ``(account_id, account_name, is_equity,
            gains_eur, losses_eur, trade_count, missing_count)`` with one row
            per category and account that has at least one trade.

            Each tuple contains:
            - ``account_id`` (UUID | None): The account ID.
            - ``account_name`` (str | None): The account name.
            - ``is_equity`` (bool): ``True`` for equity, ``False`` for derivatives.
            - ``gains_eur`` (Decimal): Sum of positive ``COALESCE(pnl_eur, pnl)``.
            - ``losses_eur`` (Decimal): Sum of negative ``COALESCE(pnl_eur, pnl)``
              (always <= 0).
            - ``trade_count`` (int): Total count of closed trades.
            - ``missing_count`` (int): Trades where ``pnl_eur`` is NULL.
        """
        is_equity_expr = case(
            (Trade.asset_class == AssetClass.EQUITY, True),
            else_=False,
        )

        # Use pnl_eur when available; fall back to pnl (original currency) when the
        # Bundesbank EUR conversion was not available at import time.
        effective_pnl = func.coalesce(Trade.pnl_eur, Trade.pnl)

        gains_expr = func.coalesce(
            func.sum(
                case(
                    (effective_pnl > 0, effective_pnl),
                    else_=None,
                )
            ),
            Decimal("0"),
        )

        losses_expr = func.coalesce(
            func.sum(
                case(
                    (effective_pnl < 0, effective_pnl),
                    else_=None,
                )
            ),
            Decimal("0"),
        )

        trade_count_expr = func.count(Trade.pnl)  # COUNT ignores NULLs; pnl is always set for closed trades.

        missing_count_expr = func.count(
            case(
                (Trade.pnl_eur.is_(None), 1),
                else_=None,
            )
        )

        stmt = (
            select(
                Account.id.label("account_id"),
                Account.name.label("account_name"),
                is_equity_expr.label("is_equity"),
                gains_expr.label("gains_eur"),
                losses_expr.label("losses_eur"),
                trade_count_expr.label("trade_count"),
                missing_count_expr.label("missing_count"),
            )
            .outerjoin(Account, Trade.account_id == Account.id)
            .where(
                and_(
                    Trade.user_id == user_id,
                    Trade.pnl.is_not(None),  # Only closed trades.
                    extract("year", Trade.closed_at) == year,
                )
            )
            .group_by(Account.id, Account.name, is_equity_expr)
        )

        result = await session.execute(stmt)
        rows = result.all()
        output: list[tuple[uuid.UUID | None, str | None, bool, Decimal, Decimal, int, int]] = [
            (
                row.account_id,
                row.account_name,
                bool(row.is_equity),
                Decimal(str(row.gains_eur)),
                Decimal(str(row.losses_eur)),
                int(row.trade_count),
                int(row.missing_count),
            )
            for row in rows
        ]
        return output

    async def get_annual_trades(
        self,
        session: AsyncSession,
        year: int,
        user_id: uuid.UUID,
    ) -> list[Trade]:
        """Fetch individual closed trades for a given year and user.

        Used by the CSV export endpoint.  Returns all closed trades (those
        where ``pnl IS NOT NULL``) ordered by ``closed_at`` ascending,
        regardless of whether ``pnl_eur`` is set.

        Args:
            session: Active async SQLAlchemy session.
            year: Calendar year to filter on (based on ``closed_at``).
            user_id: UUID of the authenticated user.

        Returns:
            A list of :class:`~app.models.trade.Trade` ORM instances ordered
            by ``closed_at`` ascending.
        """
        stmt = (
            select(Trade)
            .options(joinedload(Trade.account))
            .where(
                and_(
                    Trade.user_id == user_id,
                    Trade.pnl.is_not(None),  # Only closed trades.
                    extract("year", Trade.closed_at) == year,
                )
            )
            .order_by(Trade.closed_at)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_cash_flow_rows(
        self,
        session: AsyncSession,
        year: int,
        user_id: uuid.UUID,
    ) -> list[tuple[uuid.UUID | None, Decimal, Decimal, Decimal]]:
        """Aggregate cash transactions for dividends, withholding tax and interest.

        Returns one row per account containing the EUR totals for the three
        tax-relevant cash-flow categories for the given year.

        Only cash transactions with a non-NULL ``amount_eur`` are included in
        the monetary totals.  Rows are grouped by ``account_id``.

        Args:
            session: Active async SQLAlchemy session.
            year: Calendar year to filter on (based on ``date``).
            user_id: UUID of the authenticated user (via account join).

        Returns:
            A list of 4-tuples ``(account_id, dividends_eur, withholding_tax_eur,
            interest_eur)`` — one tuple per account that has at least one
            matching cash transaction in the given year.
        """
        # Use amount_eur when available, fall back to amount (raw currency)
        # This handles the case where Bundesbank FX lookup fails during import.
        eur_amount = func.coalesce(CashTransaction.amount_eur, CashTransaction.amount)

        dividends_expr = func.coalesce(
            func.sum(
                case(
                    (
                        CashTransaction.type == CashTransactionType.DIVIDEND,
                        eur_amount,
                    ),
                    else_=None,
                )
            ),
            Decimal("0"),
        )
        withholding_expr = func.coalesce(
            func.sum(
                case(
                    (
                        CashTransaction.type == CashTransactionType.WITHHOLDING_TAX,
                        eur_amount,
                    ),
                    else_=None,
                )
            ),
            Decimal("0"),
        )
        interest_expr = func.coalesce(
            func.sum(
                case(
                    (
                        CashTransaction.type == CashTransactionType.INTEREST,
                        eur_amount,
                    ),
                    else_=None,
                )
            ),
            Decimal("0"),
        )

        stmt = (
            select(
                CashTransaction.account_id.label("account_id"),
                dividends_expr.label("dividends_eur"),
                withholding_expr.label("withholding_tax_eur"),
                interest_expr.label("interest_eur"),
            )
            .join(Account, CashTransaction.account_id == Account.id)
            .where(
                and_(
                    Account.user_id == user_id,
                    extract("year", CashTransaction.date) == year,
                    CashTransaction.type.in_(
                        [
                            CashTransactionType.DIVIDEND,
                            CashTransactionType.WITHHOLDING_TAX,
                            CashTransactionType.INTEREST,
                        ]
                    ),
                )
            )
            .group_by(CashTransaction.account_id)
        )

        result = await session.execute(stmt)
        rows = result.all()
        return [
            (
                row.account_id,
                Decimal(str(row.dividends_eur)),
                Decimal(str(row.withholding_tax_eur)),
                Decimal(str(row.interest_eur)),
            )
            for row in rows
        ]

    async def get_annual_cash_transactions(
        self,
        session: AsyncSession,
        year: int,
        user_id: uuid.UUID,
    ) -> list[CashTransaction]:
        """Fetch individual cash transactions for the CSV export.

        Returns DIVIDEND, WITHHOLDING_TAX and INTEREST cash transactions for
        the given year and user, ordered by ``date`` ascending.

        Args:
            session: Active async SQLAlchemy session.
            year: Calendar year to filter on (based on ``date``).
            user_id: UUID of the authenticated user.

        Returns:
            A list of :class:`~app.models.cash_transaction.CashTransaction`
            ORM instances.
        """
        stmt = (
            select(CashTransaction)
            .options(joinedload(CashTransaction.account))
            .join(Account, CashTransaction.account_id == Account.id)
            .where(
                and_(
                    Account.user_id == user_id,
                    extract("year", CashTransaction.date) == year,
                    CashTransaction.type.in_(
                        [
                            CashTransactionType.DIVIDEND,
                            CashTransactionType.WITHHOLDING_TAX,
                            CashTransactionType.INTEREST,
                        ]
                    ),
                )
            )
            .order_by(CashTransaction.date)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
