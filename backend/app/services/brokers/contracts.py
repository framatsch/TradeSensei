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

"""Contract every broker integration implements.

A broker is one :class:`BrokerAdapter`: a broker key, the
:class:`~app.models.account.AccountType` it serves, an :class:`ImportPolicy`
and an explicit, optional slot per capability. Capabilities are
:class:`typing.Protocol` s; a ``None`` slot means "not supported" and is
rejected at the call site.

The import pipeline consumes only :class:`CanonicalImportBatch`. Executions
stay :class:`~app.schemas.broker_raw_transaction.BrokerRawTransactionCreate`
— there is deliberately no broker-specific intermediate representation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account, AccountType
from app.schemas.broker_raw_transaction import BrokerRawTransactionCreate
from app.schemas.corporate_action import CorporateActionCreateRequest


class BrokerType(StrEnum):
    """Registered broker keys."""

    IBKR = "ibkr"
    SCHWAB = "schwab"


@dataclass(frozen=True, slots=True)
class CanonicalImportBatch:
    """Everything the import pipeline needs from one broker payload.

    Attributes:
        executions: One raw record per broker execution (not yet stamped
            with user/account).
        corporate_actions: Corporate actions contained in the payload.
        warnings: Non-fatal parse warnings, in the order they occurred.
    """

    executions: list[BrokerRawTransactionCreate]
    corporate_actions: list[CorporateActionCreateRequest]
    warnings: list[str]


@dataclass(frozen=True, slots=True)
class ImportPolicy:
    """Broker-specific switches for otherwise broker-agnostic pipeline steps.

    Attributes:
        self_heal_pending_protected_close: Run the zero-insert self-heal that
            rebuilds the projection when an open metadata-protected trade has
            an absorbable unlinked execution.
    """

    self_heal_pending_protected_close: bool = False


@dataclass(frozen=True, slots=True)
class BindingResult:
    """Outcome of :meth:`AccountBindingCapability.bind`.

    Attributes:
        content: Payload reduced to the part belonging to the target account.
        bound_account_number: Broker account number that was newly bound to
            the account during this call, or ``None``.
    """

    content: bytes
    bound_account_number: str | None


@dataclass(frozen=True, slots=True)
class SyncWindow:
    """Requested history window for a remote sync.

    Attributes:
        days: Number of past days to fetch.
        from_date: Optional explicit start date (``YYYYMMDD``) for brokers
            that support it; overrides ``days``.
    """

    days: int
    from_date: str | None = None


@dataclass(frozen=True, slots=True)
class FetchedPayload:
    """Unparsed broker payload returned by a remote sync.

    Attributes:
        content: Payload bytes exactly as the file import capability accepts
            them.
        filename: Source label passed to the import pipeline.
    """

    content: bytes
    filename: str


class FileImportCapability(Protocol):
    """Pure parsing of a broker payload (no DB, no HTTP)."""

    @property
    def accepted_extensions(self) -> frozenset[str]:
        """Lower-case file extensions (without dot) accepted for upload."""
        ...

    def rejected_extension_message(self, extension: str) -> str | None:
        """Return a broker-specific rejection message for ``extension``, if any."""
        ...

    def parse(self, content: bytes, filename: str) -> CanonicalImportBatch:
        """Parse ``content`` into a canonical batch.

        Raises:
            ImportParseError: If the payload cannot be parsed at all.
        """
        ...


class AccountBindingCapability(Protocol):
    """Selects the payload part for an account and may bind its number."""

    async def bind(self, content: bytes, account: Account, session: AsyncSession) -> BindingResult:
        """Reduce ``content`` to ``account`` and bind an unset account number.

        Raises:
            ImportParseError: If the payload is malformed.
            ImportAccountMismatchError: If no / an ambiguous entry matches.
        """
        ...


class RemoteSyncCapability(Protocol):
    """Fetches a broker payload; never parses, aggregates or persists trades."""

    async def fetch(self, account: Account, window: SyncWindow, session: AsyncSession) -> FetchedPayload:
        """Fetch the payload for ``account``.

        Raises:
            ConfigurationError: If credentials are missing or the broker
                rejects the request.
            UpstreamServiceUnavailableError: If the broker is temporarily
                unavailable.
        """
        ...


class ConnectionCapability(Protocol):
    """Validates broker credentials without persisting changes."""

    async def test(self, provided: dict[str, str], account: Account | None, session: AsyncSession) -> None:
        """Validate credentials from ``provided`` or the stored account.

        Raises:
            ConfigurationError: If the credentials are missing or invalid.
        """
        ...


@dataclass(frozen=True, slots=True)
class BrokerAdapter:
    """One broker integration.

    Attributes:
        key: Unique broker key.
        account_type: The account type served by this broker.
        policy: Broker-specific pipeline switches.
        file_import: File/payload parsing, or ``None``.
        account_binding: Payload-to-account binding, or ``None``.
        remote_sync: Remote payload fetch, or ``None``.
        connection: Credential validation, or ``None``.
    """

    key: BrokerType
    account_type: AccountType
    policy: ImportPolicy
    file_import: FileImportCapability | None = None
    account_binding: AccountBindingCapability | None = None
    remote_sync: RemoteSyncCapability | None = None
    connection: ConnectionCapability | None = None
