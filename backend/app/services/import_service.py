"""Business-logic service for broker file import operations.

Orchestrates broker file parsing and bulk trade creation for a given
account.  No HTTP concepts appear in this layer.
"""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AccountNotFoundError
from app.repositories.account_repository import AccountRepository
from app.repositories.trade_repository import TradeRepository
from app.schemas.imports import ImportResult
from app.schemas.trade import TradeCreate
from app.utils.parsers.base import BrokerParser
from app.utils.parsers.factory import BrokerType, get_parser

logger = logging.getLogger(__name__)


class ImportService:
    """Service layer for importing broker trade files.

    Validates account ownership, delegates to the appropriate broker
    parser, and bulk-creates the parsed trades.

    Args:
        session: An open :class:`~sqlalchemy.ext.asyncio.AsyncSession`
            managed by the caller.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with a database session.

        Args:
            session: The session to use for all operations within this
                request.
        """
        self._session = session
        self._account_repo = AccountRepository(session)
        self._trade_repo = TradeRepository(session)

    async def import_file(
        self,
        content: bytes,
        filename: str,
        broker: BrokerType,
        account_id: uuid.UUID | None,
        user_id: uuid.UUID,
    ) -> ImportResult:
        """Parse a broker export file and bulk-create trades for an account.

        The method first verifies that the target account belongs to the
        requesting user (if ``account_id`` is provided).  It then hands the
        raw bytes to the appropriate broker parser, optionally sets
        ``account_id`` on each parsed
        :class:`~app.schemas.trade.TradeCreate`, and persists them via
        :class:`~app.repositories.trade_repository.TradeRepository`.

        All inserts happen within the caller's transaction; the service
        does **not** commit — that responsibility belongs to the route handler.

        Args:
            content: Raw file bytes from the upload.
            filename: Original filename (used by the parser for format
                detection).
            broker: The broker type that identifies which parser to use.
            account_id: Optional UUID of the account to associate trades
                with.  When ``None`` trades are created without an account
                association.
            user_id: UUID of the authenticated user — used to verify
                account ownership when ``account_id`` is given.

        Returns:
            An :class:`~app.schemas.imports.ImportResult` summarising the
            outcome of the import.

        Raises:
            AccountNotFoundError: If ``account_id`` is provided but the
                account does not exist or does not belong to ``user_id``.
        """
        # Verify the account belongs to the requesting user (only if provided).
        if account_id is not None:
            account = await self._account_repo.get_by_id(account_id, user_id)
            if account is None:
                raise AccountNotFoundError(
                    f"Account {account_id} not found for user {user_id}."
                )

        parser: BrokerParser = get_parser(broker)
        parsed_trades: list[TradeCreate] = parser.parse(content, filename)

        # Enrich pnl_eur — base class provides a no-op default so this is always safe.
        await parser.enrich_pnl_eur(parsed_trades, self._session)

        # Collect parser warnings (IBKRParser / SchwabParser expose .warnings).
        parser_warnings: list[str] = getattr(parser, "warnings", [])

        trades_created = 0
        create_warnings: list[str] = []

        for trade_data in parsed_trades:
            # Stamp both account_id and user_id onto each trade before persisting.
            trade_with_owner = trade_data.model_copy(
                update={"account_id": account_id, "user_id": user_id}
            )
            try:
                await self._trade_repo.create(trade_with_owner)
                trades_created += 1
            except Exception as exc:  # noqa: BLE001
                msg = (
                    f"Failed to persist trade {trade_data.symbol} "
                    f"opened at {trade_data.opened_at}: {exc}"
                )
                logger.warning(msg)
                create_warnings.append(msg)

        all_warnings = parser_warnings + create_warnings
        trades_skipped = len(parsed_trades) - trades_created

        return ImportResult(
            broker=str(broker),
            filename=filename,
            trades_parsed=len(parsed_trades),
            trades_created=trades_created,
            trades_skipped=trades_skipped,
            warnings=all_warnings,
        )
