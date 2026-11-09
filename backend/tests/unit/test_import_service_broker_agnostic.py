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

"""Guard: the import pipeline must not branch on a specific broker.

Broker-specific behavior belongs in adapter capabilities and policy flags
(``app/services/brokers``). See the ``broker-adapter-contract`` spec.
"""

import inspect
import re

import pytest

from app.services import import_service

pytestmark = pytest.mark.unit

_FORBIDDEN = re.compile(r"\b(?:BrokerType|AccountType)\.(?:IBKR|SCHWAB)\b")
_FORBIDDEN_IMPORTS = (
    "app.utils.parsers.ibkr_xml",
    "app.utils.parsers.schwab_json",
    "app.utils.parsers.factory",
    "app.services.brokers.ibkr",
    "app.services.brokers.schwab",
)


def test_import_service_has_no_broker_member_references() -> None:
    source = inspect.getsource(import_service)
    assert _FORBIDDEN.findall(source) == []


def test_import_service_does_not_import_broker_specific_modules() -> None:
    source = inspect.getsource(import_service)
    for module in _FORBIDDEN_IMPORTS:
        assert module not in source, module
