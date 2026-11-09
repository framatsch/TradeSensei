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

"""Test helpers for substituting broker adapters in ``ImportService`` unit tests."""

from __future__ import annotations

import dataclasses
from typing import Any

from app.services.brokers.contracts import BrokerAdapter, BrokerType, CanonicalImportBatch
from app.services.brokers.registry import get_adapter


class _MockParserFileImport:
    """File-import capability that delegates to a mocked parser's ``parse_raw``."""

    def __init__(self, parser: Any, accepted_extensions: frozenset[str]) -> None:
        self._parser = parser
        self.accepted_extensions = accepted_extensions

    def rejected_extension_message(self, extension: str) -> str | None:
        del extension
        return None

    def parse(self, content: bytes, filename: str) -> CanonicalImportBatch:
        executions, corporate_actions = self._parser.parse_raw(content, filename)
        return CanonicalImportBatch(
            executions=list(executions),
            corporate_actions=list(corporate_actions),
            warnings=list(self._parser.warnings),
        )


def adapter_from_mock_parser(parser: Any, broker: BrokerType = BrokerType.IBKR) -> BrokerAdapter:
    """Return the registered adapter for ``broker`` with its file import backed by ``parser``.

    ``parser.parse_raw`` must return ``(executions, corporate_actions)`` and
    ``parser.warnings`` must be a list — the same shape real parsers expose.
    """
    base = get_adapter(broker)
    assert base.file_import is not None
    return dataclasses.replace(base, file_import=_MockParserFileImport(parser, base.file_import.accepted_extensions))
