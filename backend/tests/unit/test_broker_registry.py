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

"""Unit tests for the broker adapter registry and the adapter file imports."""

import json
from pathlib import Path

import pytest

from app.core.exceptions import ImportParseError, UnsupportedBrokerError
from app.models.account import AccountType
from app.services.brokers.contracts import BrokerType, CanonicalImportBatch
from app.services.brokers.registry import adapter_for_account_type, get_adapter, registered_adapters
from app.utils.parsers.ibkr_xml import IBKRXMLParser
from app.utils.parsers.schwab_json import SchwabJSONParser

pytestmark = pytest.mark.unit

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_get_adapter_resolves_every_broker_key() -> None:
    assert get_adapter(BrokerType.IBKR).key is BrokerType.IBKR
    assert get_adapter(BrokerType.SCHWAB).key is BrokerType.SCHWAB
    assert {adapter.key for adapter in registered_adapters()} == set(BrokerType)


def test_get_adapter_unknown_key_raises_unsupported_broker() -> None:
    with pytest.raises(UnsupportedBrokerError, match="No parser available for broker 'tastytrade'"):
        get_adapter("tastytrade")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("account_type", "expected"),
    [(AccountType.IBKR, BrokerType.IBKR), (AccountType.SCHWAB, BrokerType.SCHWAB)],
)
def test_adapter_for_account_type(account_type: AccountType, expected: BrokerType) -> None:
    adapter = adapter_for_account_type(account_type)
    assert adapter is not None
    assert adapter.key is expected
    assert adapter.account_type is account_type


def test_account_type_without_adapter_returns_none() -> None:
    assert adapter_for_account_type(AccountType.MANUAL) is None


@pytest.mark.parametrize(
    ("key", "extensions"),
    [(BrokerType.IBKR, frozenset({"xml"})), (BrokerType.SCHWAB, frozenset({"json"}))],
)
def test_file_import_extension_sets(key: BrokerType, extensions: frozenset[str]) -> None:
    file_import = get_adapter(key).file_import
    assert file_import is not None
    assert file_import.accepted_extensions == extensions


def test_rejected_extension_messages() -> None:
    schwab = get_adapter(BrokerType.SCHWAB).file_import
    ibkr = get_adapter(BrokerType.IBKR).file_import
    assert schwab is not None and ibkr is not None
    assert schwab.rejected_extension_message("csv") == "Schwab accounts require JSON format (.json). CSV import is no longer supported."
    assert schwab.rejected_extension_message("xml") is None
    assert ibkr.rejected_extension_message("csv") is None


def test_import_policy_flags() -> None:
    assert get_adapter(BrokerType.SCHWAB).policy.self_heal_pending_protected_close is True
    assert get_adapter(BrokerType.IBKR).policy.self_heal_pending_protected_close is False


def test_every_registered_file_adapter_returns_a_batch() -> None:
    """Guards against reintroducing a parser-specific fallback in the pipeline."""
    samples = {
        BrokerType.IBKR: (_FIXTURES / "ibkr" / "combo_flip_edge_cases.xml").read_bytes(),
        BrokerType.SCHWAB: (_FIXTURES / "schwab" / "schwab_golden_multi_account.json").read_bytes(),
    }
    for adapter in registered_adapters():
        assert adapter.file_import is not None, adapter.key
        batch = adapter.file_import.parse(samples[adapter.key], "sample")
        assert isinstance(batch, CanonicalImportBatch)
        assert batch.executions


def test_ibkr_batch_matches_parser_output_including_warnings() -> None:
    content = (_FIXTURES / "ibkr" / "combo_flip_edge_cases.xml").read_bytes()
    parser = IBKRXMLParser()
    records, corporate_actions = parser.parse_raw(content, "x.xml")

    file_import = get_adapter(BrokerType.IBKR).file_import
    assert file_import is not None
    batch = file_import.parse(content, "x.xml")

    assert batch.executions == records
    assert batch.corporate_actions == corporate_actions
    assert batch.warnings == parser.warnings
    assert batch.warnings == [
        "<Trade> element 20: skipped — missing symbol attribute.",
        "<Trade> element 21 (ZERO): skipped — quantity is zero.",
        "<Trade> element 22 (NODT): skipped — missing tradeDate.",
    ]


def test_schwab_batch_matches_parser_output_including_warnings() -> None:
    content = (_FIXTURES / "schwab" / "schwab_golden_multi_account.json").read_bytes()
    parser = SchwabJSONParser()
    records, corporate_actions = parser.parse_raw(content, "x.json")

    file_import = get_adapter(BrokerType.SCHWAB).file_import
    assert file_import is not None
    batch = file_import.parse(content, "x.json")

    assert batch.executions == records
    assert batch.corporate_actions == corporate_actions == []
    assert batch.warnings == parser.warnings
    assert len(batch.warnings) == 4


def test_file_import_warnings_do_not_leak_between_calls() -> None:
    file_import = get_adapter(BrokerType.SCHWAB).file_import
    assert file_import is not None
    noisy = (_FIXTURES / "schwab" / "schwab_golden_multi_account.json").read_bytes()
    clean = json.dumps({"accounts": [{"accountNumber": "1", "transactions": []}]}).encode()

    assert file_import.parse(noisy, "a.json").warnings
    assert file_import.parse(clean, "b.json").warnings == []


def test_file_import_propagates_parse_errors() -> None:
    file_import = get_adapter(BrokerType.SCHWAB).file_import
    assert file_import is not None
    with pytest.raises(ImportParseError):
        file_import.parse(b"[]", "legacy.json")
