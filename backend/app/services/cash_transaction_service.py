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

"""Service layer for cash transactions.

Handles business logic and orchestrates repositories.
"""

import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AccountNotFoundError, CashTransactionNotFoundError
from app.models.cash_transaction import CashTransaction
from app.repositories.account_repository import AccountRepository
from app.repositories.cash_transaction_repository import CashTransactionRepository
from app.schemas.cash_transaction import (
    CashTransactionCreateRequest,
    CashTransactionFilterParams,
    CashTransactionUpdate,
)
from app.services.fx_rate_service import FxRateService


class CashTransactionService:
    """Service for managing cash transactions."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the cash transaction service.

        Args:
            session: Database session scoped to the current request.
        """
        self._session = session
        self._account_repo = AccountRepository(session)

    async def _ensure_account(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID,
        portfolio_id: uuid.UUID,
    ) -> None:
        """Ensure the requested account exists and belongs to the user."""
        account = await self._account_repo.get_by_id(account_id, user_id, portfolio_id)
        if account is None:
            raise AccountNotFoundError(f"Account {account_id} not found.")

    async def create(
        self,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID,
        account_id: uuid.UUID,
        create_request: CashTransactionCreateRequest,
    ) -> CashTransaction:
        """Create a new cash transaction.

        Args:
            user_id: The ID of the authenticated user.
            account_id: The ID of the account.
            create_request: The cash transaction data.

        Returns:
            The created cash transaction.

        Raises:
            AccountNotFoundError: If the account does not exist or user lacks access.
        """
        await self._ensure_account(user_id, account_id, portfolio_id)

        # Convert to internal schema
        create_schema = create_request.to_cash_transaction_create(account_id)

        # Auto-compute amount_eur if not provided
        if create_schema.amount_eur is None:
            if create_schema.currency == "EUR":
                create_schema.amount_eur = create_schema.amount
            elif create_schema.currency == "USD":
                fx_service = FxRateService()
                rate = await fx_service.get_usd_to_eur(self._session, create_schema.date.date())
                if rate:
                    create_schema.amount_eur = create_schema.amount * rate

        transaction = await CashTransactionRepository.create(self._session, create_schema)
        return transaction

    async def get(
        self,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID,
        account_id: uuid.UUID,
        transaction_id: uuid.UUID,
    ) -> CashTransaction:
        """Get a single cash transaction by ID.

        Args:
            user_id: The ID of the authenticated user.
            account_id: The ID of the account.
            transaction_id: The ID of the transaction.

        Returns:
            The requested cash transaction.

        Raises:
            AccountNotFoundError: If the account does not exist or user lacks access.
            CashTransactionNotFoundError: If the transaction does not exist.
        """
        await self._ensure_account(user_id, account_id, portfolio_id)

        transaction = await CashTransactionRepository.get_by_account_id(
            self._session,
            account_id,
            portfolio_id,
            user_id,
            transaction_id,
        )
        if not transaction:
            raise CashTransactionNotFoundError(f"Cash transaction {transaction_id} not found.")

        return transaction

    async def list_by_account(
        self,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID,
        account_id: uuid.UUID,
        filters: CashTransactionFilterParams,
        limit: int,
        offset: int,
    ) -> tuple[Sequence[CashTransaction], int]:
        """List cash transactions for an account.

        Args:
            user_id: The ID of the authenticated user.
            account_id: The ID of the account.
            filters: Filter parameters.
            limit: Pagination limit.
            offset: Pagination offset.

        Returns:
            A tuple containing a sequence of transactions and the total count.

        Raises:
            AccountNotFoundError: If the account does not exist or user lacks access.
        """
        await self._ensure_account(user_id, account_id, portfolio_id)

        transactions = await CashTransactionRepository.list_by_account(
            self._session,
            account_id,
            portfolio_id,
            user_id,
            filters,
            limit,
            offset,
        )
        total_count = await CashTransactionRepository.count_by_account(
            self._session,
            account_id,
            portfolio_id,
            user_id,
            filters,
        )

        return transactions, total_count

    async def update(
        self,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID,
        account_id: uuid.UUID,
        transaction_id: uuid.UUID,
        update_schema: CashTransactionUpdate,
    ) -> CashTransaction:
        """Update a cash transaction.

        Args:
            user_id: The ID of the authenticated user.
            account_id: The ID of the account.
            transaction_id: The ID of the transaction to update.
            update_schema: The update data.

        Returns:
            The updated cash transaction.

        Raises:
            AccountNotFoundError: If the account does not exist or user lacks access.
            CashTransactionNotFoundError: If the transaction does not exist.
        """
        transaction = await self.get(
            user_id=user_id,
            portfolio_id=portfolio_id,
            account_id=account_id,
            transaction_id=transaction_id,
        )

        # Re-compute EUR amount if amount or currency changed and no explicit
        # EUR amount provided
        if update_schema.amount_eur is None and (update_schema.amount is not None or update_schema.currency is not None):
            new_amount = update_schema.amount if update_schema.amount is not None else transaction.amount
            new_currency = update_schema.currency if update_schema.currency is not None else transaction.currency
            new_date = update_schema.date if update_schema.date is not None else transaction.date

            if new_currency == "EUR":
                update_schema.amount_eur = new_amount
            elif new_currency == "USD":
                fx_service = FxRateService()
                rate = await fx_service.get_usd_to_eur(self._session, new_date.date())
                if rate:
                    update_schema.amount_eur = new_amount * rate
                else:
                    update_schema.amount_eur = None
            else:
                update_schema.amount_eur = None

        updated_transaction = await CashTransactionRepository.update(self._session, transaction, update_schema)
        return updated_transaction

    async def delete(
        self,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID,
        account_id: uuid.UUID,
        transaction_id: uuid.UUID,
    ) -> None:
        """Delete a cash transaction.

        Args:
            user_id: The ID of the authenticated user.
            account_id: The ID of the account.
            transaction_id: The ID of the transaction to delete.

        Raises:
            AccountNotFoundError: If the account does not exist or user lacks access.
            CashTransactionNotFoundError: If the transaction does not exist.
        """
        transaction = await self.get(
            user_id=user_id,
            portfolio_id=portfolio_id,
            account_id=account_id,
            transaction_id=transaction_id,
        )
        await CashTransactionRepository.delete(self._session, transaction.id)
