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

from app.schemas.broker_raw_transaction import BrokerRawTransactionCreate
from app.schemas.corporate_action import CorporateActionCreateRequest


class BrokerParser(ABC):
    """Abstract base class for broker file parsers.

    Concrete subclasses implement :meth:`parse_raw` for a specific broker's
    export format. Parsers operate on raw bytes, have no side effects and no
    dependencies on the database or HTTP layer. Non-fatal per-row problems
    are collected in a ``warnings`` list on the parser instance; broker
    adapters hand them to the import pipeline inside the canonical batch.
    """

    @abstractmethod
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
        per broker execution — no FIFO aggregation is performed.

        Args:
            content: Raw file bytes.
            filename: Original filename.

        Returns:
            A tuple of:
            - List of
              :class:`~app.schemas.broker_raw_transaction.BrokerRawTransactionCreate`
            - List of :class:`~app.schemas.corporate_action.CorporateActionCreateRequest`

        Raises:
            ImportParseError: If the file cannot be parsed.
        """
