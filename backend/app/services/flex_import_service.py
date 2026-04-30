"""Business-logic service for IBKR Flex Query automatic trade import.

Orchestrates the two-step IBKR Flex Web Service workflow:

1. Request report generation via ``FlexStatementService.SendRequest``
2. Poll ``FlexStatementService.GetStatement`` until the report is ready
3. Parse the returned XML with :class:`~app.utils.parsers.ibkr_xml.IBKRXMLParser`
4. Persist the parsed trades, skipping duplicates (same symbol + opened_at +
   user_id already in the database)

No HTTP concepts from FastAPI appear in this layer.
"""

import asyncio
import logging
import re
import uuid
import xml.etree.ElementTree as ET

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    FLEX_API_VERSION,
    FLEX_BASE_URL,
    FLEX_POLL_INTERVAL_SECONDS,
    FLEX_POLL_MAX_ATTEMPTS,
)
from app.core.exceptions import AccountNotFoundError, FlexAPIError, RateLimitError
from app.repositories.account_repository import AccountRepository
from app.repositories.portfolio_repository import PortfolioRepository
from app.repositories.trade_repository import TradeRepository
from app.schemas.imports import ImportResult
from app.utils.parsers.ibkr_xml import IBKRXMLParser

logger = logging.getLogger(__name__)


class FlexImportService:
    """Service for importing trades via the IBKR Flex Web Service API.

    Wraps the two-step Flex API call (send request → poll for result),
    parses the returned XML, deduplicates against existing trades and
    persists the new ones.

    Args:
        session: An open :class:`~sqlalchemy.ext.asyncio.AsyncSession`
            managed by the caller.
        flex_token: IBKR Flex Web Service token.  Typically read from
            application settings by the caller.
        http_timeout: Timeout in seconds for individual HTTP requests
            to the Flex API.
    """

    def __init__(
        self,
        session: AsyncSession,
        flex_token: str,
        http_timeout: int = 60,
    ) -> None:
        """Initialise the service.

        Args:
            session: Database session for all repository operations.
            flex_token: IBKR Flex Web Service token.
            http_timeout: Per-request timeout in seconds.
        """
        self._session = session
        self._token = flex_token
        self._timeout = http_timeout
        self._account_repo = AccountRepository(session)
        self._portfolio_repo = PortfolioRepository(session)
        self._trade_repo = TradeRepository(session)
        self._parser = IBKRXMLParser()

    # ─── Public method ────────────────────────────────────────────────────────

    async def import_flex(
        self,
        query_id: str,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID,
        account_id: uuid.UUID | None = None,
        from_date: str | None = None,
        overwrite_manually_edited: bool = False,
    ) -> ImportResult:
        """Fetch a Flex Query report and import all contained trades.

        Args:
            query_id: IBKR Flex Query ID (configured in Account Management).
            user_id: UUID of the authenticated user.
            account_id: Optional target broker account UUID.  When supplied,
                the account must belong to ``user_id``.
            from_date: Optional start date in ``YYYYMMDD`` format passed to
                the Flex API to restrict the report period.
            overwrite_manually_edited: When ``True``, trades that have been
                manually edited are overwritten instead of skipped.

        Returns:
            An :class:`~app.schemas.imports.ImportResult` summarising the
            outcome.

        Raises:
            AccountNotFoundError: If ``account_id`` is given but does not
                belong to ``user_id``.
            FlexAPIError: If the Flex API returns an error.
            RateLimitError: If the Flex API rate-limit is hit (includes
                ``wait_seconds``).
        """
        # Verify account ownership when provided.
        if account_id is not None:
            account = await self._account_repo.get_by_id(
                account_id,
                user_id,
                portfolio_id,
            )
            if account is None:
                raise AccountNotFoundError(
                    f"Account {account_id} not found for user {user_id}."
                )

        xml_string = await self._fetch_flex_xml(query_id, from_date)
        parsed_trades, parsed_cash_txs = self._parser.parse(
            xml_string.encode("utf-8"), filename="flex_query.xml"
        )
        parser_warnings: list[str] = list(self._parser.warnings)
        portfolio_base_currency: str | None = None
        portfolio = await self._portfolio_repo.get_by_id(portfolio_id, user_id)
        if portfolio is not None:
            portfolio_base_currency = portfolio.base_currency

        # Load manually-edited keys once for the whole batch (skip when
        # overwrite_manually_edited is requested).
        manually_edited_keys = (
            await self._trade_repo.list_manually_edited_keys(user_id, portfolio_id)
            if not overwrite_manually_edited
            else set()
        )

        trades_created = 0
        trades_skipped = 0
        cash_txs_created = 0
        cash_txs_skipped = 0
        create_warnings: list[str] = []

        for trade_data in parsed_trades:
            trade_with_owner = trade_data.model_copy(
                update={"account_id": account_id, "user_id": user_id}
            )

            # Skip trades the user has manually corrected (unless overwriting).
            match_key = (trade_with_owner.broker_conid, trade_with_owner.opened_at)
            if match_key in manually_edited_keys:
                trades_skipped += 1
                logger.debug(
                    "Skipping re-import of manually-edited trade: "
                    "symbol=%s opened_at=%s",
                    trade_with_owner.symbol,
                    trade_with_owner.opened_at,
                )
                continue

            # Duplicate check: same user + symbol + opened_at already exists.
            if await self._trade_repo.find_duplicate(
                user_id=user_id,
                symbol=trade_with_owner.symbol,
                opened_at=trade_with_owner.opened_at,
                portfolio_id=portfolio_id,
            ):
                trades_skipped += 1
                logger.debug(
                    "Skipping duplicate trade: %s @ %s",
                    trade_with_owner.symbol,
                    trade_with_owner.opened_at,
                )
                continue

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
                trades_skipped += 1

        if account_id is not None:
            # Import here to avoid circular dependencies if needed, or at the top
            from app.repositories.cash_transaction_repository import (
                CashTransactionRepository,
            )
            from app.services.cash_transaction_service import CashTransactionService

            cash_service = CashTransactionService(self._session)
            for cash_tx_data in parsed_cash_txs:
                # Duplicate check: same account + date + type + amount + symbol
                is_dup = await CashTransactionRepository.find_duplicate(
                    self._session,
                    account_id=account_id,
                    date=cash_tx_data.date,
                    tx_type=cash_tx_data.type,
                    amount=cash_tx_data.amount,
                    symbol=cash_tx_data.symbol,
                )
                if is_dup:
                    logger.debug(
                        "Skipping duplicate cash transaction: %s %s @ %s",
                        cash_tx_data.type,
                        cash_tx_data.symbol,
                        cash_tx_data.date,
                    )
                    cash_txs_skipped += 1
                    continue

                try:
                    await cash_service.create(
                        user_id=user_id,
                        portfolio_id=portfolio_id,
                        account_id=account_id,
                        create_request=cash_tx_data,
                    )
                    cash_txs_created += 1
                except Exception as exc:  # noqa: BLE001
                    msg = (
                        f"Failed to persist cash transaction "
                        f"at {cash_tx_data.date}: {exc}"
                    )
                    logger.warning(msg)
                    create_warnings.append(msg)
                    cash_txs_skipped += 1
        else:
            cash_txs_skipped += len(parsed_cash_txs)

        all_warnings = parser_warnings + create_warnings

        if portfolio_base_currency is not None:
            mismatched_count = sum(
                1
                for trade_data in parsed_trades
                if trade_data.currency is not None
                and trade_data.currency != portfolio_base_currency
            )
            if mismatched_count > 0:
                all_warnings.append(
                    "currency_mismatch: "
                    f"{mismatched_count} imported trade(s) use a currency "
                    "different from portfolio "
                    f"base_currency '{portfolio_base_currency}'."
                )

        return ImportResult(
            broker="ibkr",
            filename=f"flex_query_{query_id}.xml",
            trades_parsed=len(parsed_trades),
            trades_created=trades_created,
            trades_skipped=trades_skipped,
            cash_transactions_parsed=len(parsed_cash_txs),
            cash_transactions_created=cash_txs_created,
            cash_transactions_skipped=cash_txs_skipped,
            warnings=all_warnings,
        )

    # ─── Flex API helpers ─────────────────────────────────────────────────────

    async def _fetch_flex_xml(self, query_id: str, from_date: str | None) -> str:
        """Execute the two-step Flex API request-and-poll workflow.

        Args:
            query_id: IBKR Flex Query ID.
            from_date: Optional start date in ``YYYYMMDD`` format.

        Returns:
            Raw XML string of the Flex Query report.

        Raises:
            FlexAPIError: On any Flex API error.
            RateLimitError: When IBKR rate-limits the request (error 1019).
        """
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            reference_code = await self._send_request(client, query_id, from_date)
            return await self._poll_report(client, reference_code)

    async def _send_request(
        self,
        client: httpx.AsyncClient,
        query_id: str,
        from_date: str | None,
    ) -> str:
        """Send the initial Flex Query generation request.

        Args:
            client: Shared :class:`httpx.AsyncClient` instance.
            query_id: IBKR Flex Query ID.
            from_date: Optional start date filter (``YYYYMMDD``).

        Returns:
            The ``ReferenceCode`` to use for polling.

        Raises:
            FlexAPIError: On HTTP or API-level errors.
            RateLimitError: When IBKR responds with error code ``1019``.
        """
        params: dict[str, str] = {
            "t": self._token,
            "q": query_id,
            "v": FLEX_API_VERSION,
        }
        if from_date:
            params["period"] = from_date

        url = f"{FLEX_BASE_URL}/FlexStatementService.SendRequest"
        logger.info("Requesting Flex Query %s generation…", query_id)

        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise FlexAPIError(f"HTTP error sending Flex request: {exc}") from exc

        try:
            root = ET.fromstring(response.text)
        except ET.ParseError as exc:
            raise FlexAPIError(
                f"Invalid XML in Flex SendRequest response: {exc}"
            ) from exc

        status_elem = root.find("Status")
        if status_elem is None or status_elem.text != "Success":
            error_code = _text(root.find("ErrorCode"))
            error_msg = _text(root.find("ErrorMessage")) or "Unknown error"
            if error_code and "1019" in error_code:
                wait_seconds = _parse_wait_time(error_msg)
                raise RateLimitError(error_msg, wait_seconds)
            raise FlexAPIError(f"Flex SendRequest failed: {error_msg}")

        ref_elem = root.find("ReferenceCode")
        ref_code = _text(ref_elem)
        if not ref_code:
            raise FlexAPIError(
                "Invalid Flex SendRequest response: missing ReferenceCode."
            )

        logger.info("Flex Query generation requested; reference code: %s", ref_code)
        return ref_code

    async def _poll_report(
        self,
        client: httpx.AsyncClient,
        reference_code: str,
    ) -> str:
        """Poll the Flex API until the report is ready.

        Args:
            client: Shared :class:`httpx.AsyncClient` instance.
            reference_code: Code received from :meth:`_send_request`.

        Returns:
            XML string of the completed report.

        Raises:
            FlexAPIError: If the report fails or polling times out.
        """
        url = f"{FLEX_BASE_URL}/FlexStatementService.GetStatement"
        params = {
            "t": self._token,
            "q": reference_code,
            "v": FLEX_API_VERSION,
        }

        for attempt in range(1, FLEX_POLL_MAX_ATTEMPTS + 1):
            await asyncio.sleep(FLEX_POLL_INTERVAL_SECONDS)
            logger.debug(
                "Polling for Flex report (attempt %d/%d)…",
                attempt,
                FLEX_POLL_MAX_ATTEMPTS,
            )

            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise FlexAPIError(f"HTTP error polling Flex report: {exc}") from exc

            try:
                root = ET.fromstring(response.text)
            except ET.ParseError as exc:
                raise FlexAPIError(
                    f"Invalid XML in Flex GetStatement response: {exc}"
                ) from exc

            # Report is ready when the root element is FlexQueryResponse.
            if root.tag == "FlexQueryResponse":
                logger.info("Flex report ready after %d attempt(s).", attempt)
                return ET.tostring(root, encoding="unicode")

            # Otherwise it's a FlexStatementResponse with a status code.
            status = _text(root.find("Status"))
            code = _text(root.find("ErrorCode"))
            msg = _text(root.find("ErrorMessage")) or "Unknown"

            if status == "Warn" and code and "1018" in code:
                # 1018 = report still being generated, keep polling.
                continue

            raise FlexAPIError(f"Flex GetStatement error (status={status}): {msg}")

        raise FlexAPIError(
            f"Flex report not ready after {FLEX_POLL_MAX_ATTEMPTS} polling attempts."
        )


# ─── Module-level helpers ─────────────────────────────────────────────────────


def _text(elem: ET.Element | None) -> str | None:
    """Return the text content of an XML element, or ``None``.

    Args:
        elem: An :class:`~xml.etree.ElementTree.Element` or ``None``.

    Returns:
        The stripped text content, or ``None`` if the element is absent
        or has no text.
    """
    if elem is None:
        return None
    return (elem.text or "").strip() or None


def _parse_wait_time(error_message: str) -> int:
    """Extract the wait duration from an IBKR rate-limit error message.

    IBKR messages typically read: ``"Please try again in X minutes"``.

    Args:
        error_message: The raw IBKR error message string.

    Returns:
        Wait time in seconds.  Defaults to 900 (15 minutes) when the
        duration cannot be extracted.
    """
    match = re.search(r"(\d+)\s+minute", error_message, re.IGNORECASE)
    if match:
        return int(match.group(1)) * 60
    return 900
