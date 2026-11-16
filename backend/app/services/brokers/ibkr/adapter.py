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

"""Interactive Brokers adapter: Flex Query XML file import and Flex Web Service sync."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConfigurationError, FlexAPIError, RateLimitError, UpstreamServiceUnavailableError
from app.models.account import Account, AccountType
from app.services import flex_import_service
from app.services.brokers.contracts import (
    BrokerAdapter,
    BrokerType,
    CanonicalImportBatch,
    FetchedPayload,
    ImportPolicy,
    SyncWindow,
)
from app.services.brokers.credentials import require_portfolio_id, resolve_property
from app.utils.parsers.ibkr_xml import IBKRXMLParser

IBKR_FLEX_TOKEN_KEYS = ("ibkr_flex_token", "IBKR_FLEX_TOKEN")
IBKR_FLEX_QUERY_ID_KEYS = ("ibkr_flex_query_id", "IBKR_FLEX_QUERY_ID")


class IBKRFileImport:
    """Parses IBKR Flex Query XML (Activity and Trade Confirmation)."""

    accepted_extensions: frozenset[str] = frozenset({"xml"})

    def rejected_extension_message(self, extension: str) -> str | None:
        """IBKR has no broker-specific rejection message."""
        del extension
        return None

    def parse(self, content: bytes, filename: str) -> CanonicalImportBatch:
        """Parse Flex XML into a canonical batch; skipped rows become warnings."""
        parser = IBKRXMLParser()
        executions, corporate_actions = parser.parse_raw(content, filename)
        return CanonicalImportBatch(
            executions=executions,
            corporate_actions=corporate_actions,
            warnings=list(parser.warnings),
        )


class IBKRRemoteSync:
    """Fetches the account's Flex Query report via the IBKR Flex Web Service."""

    async def fetch(self, account: Account, window: SyncWindow, session: AsyncSession) -> FetchedPayload:
        """Fetch Flex XML from ``window.from_date`` (or ``window.days`` back).

        Raises:
            ConfigurationError: If the Flex token/query ID is missing or IBKR
                rejects the request.
            UpstreamServiceUnavailableError: On rate limiting or a transient
                report-generation delay.
        """
        del session
        flex_token = resolve_property({}, account, IBKR_FLEX_TOKEN_KEYS)
        query_id = resolve_property({}, account, IBKR_FLEX_QUERY_ID_KEYS)

        from_date = window.from_date
        if from_date is None:
            now = datetime.now(UTC)
            from_date = (now - timedelta(days=window.days)).strftime("%Y%m%d")

        flex_service = flex_import_service.FlexImportService(flex_token)
        require_portfolio_id(account)

        try:
            flex_xml = await flex_service.fetch_flex_report(
                query_id=query_id,
                from_date=from_date,
            )
        except RateLimitError as exc:
            raise UpstreamServiceUnavailableError(f"IBKR API rate limit reached: {exc}") from exc
        except FlexAPIError as exc:
            if flex_import_service.is_transient_send_request_error(str(exc)):
                raise UpstreamServiceUnavailableError(f"IBKR Flex API temporarily unavailable: {exc}") from exc
            raise ConfigurationError(f"IBKR Flex API error: {exc}") from exc
        return FetchedPayload(content=flex_xml, filename=f"flex_query_{query_id}.xml")


class IBKRConnection:
    """Validates Flex credentials by requesting a report."""

    async def test(self, provided: dict[str, str], account: Account | None, session: AsyncSession) -> None:
        """Use provided credentials, falling back to the stored account properties."""
        del session
        flex_token = resolve_property(provided, account, IBKR_FLEX_TOKEN_KEYS)
        query_id = resolve_property(provided, account, IBKR_FLEX_QUERY_ID_KEYS)

        service = flex_import_service.FlexImportService(flex_token)
        try:
            await service.fetch_flex_report(query_id=query_id, from_date=None)
        except Exception as exc:
            raise ConfigurationError(f"IBKR connection test failed: {exc}") from exc


IBKR_ADAPTER = BrokerAdapter(
    key=BrokerType.IBKR,
    account_type=AccountType.IBKR,
    policy=ImportPolicy(self_heal_pending_protected_close=False),
    file_import=IBKRFileImport(),
    remote_sync=IBKRRemoteSync(),
    connection=IBKRConnection(),
)
