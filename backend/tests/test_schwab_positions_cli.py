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

"""Unit tests for the Schwab CLI account-resolution behavior.

The shipped tool (``tools/schwab_cli.py``) imports ``schwabdev`` and ``rich``
at module load and calls ``sys.exit`` when they are missing.  These deps are
not part of the backend test environment, so the whole test module is skipped
unless both are importable.
"""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

import pytest

pytest.importorskip("schwabdev")
pytest.importorskip("rich")


def _load_cli_module() -> ModuleType:
    tool_path = Path(__file__).resolve().parents[2] / "tools" / "schwab_cli.py"
    spec = spec_from_file_location("schwab_cli", tool_path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.unit
def test_match_account_single_auto_select() -> None:
    module = _load_cli_module()
    accounts = [{"accountNumber": "12345678", "hashValue": "h1"}]

    selected = module._match_account(accounts, None)
    assert selected == accounts


@pytest.mark.unit
def test_match_account_matches_explicit_account() -> None:
    module = _load_cli_module()
    accounts = [
        {"accountNumber": "11111111", "hashValue": "h1"},
        {"accountNumber": "22222222", "hashValue": "h2"},
    ]

    selected = module._match_account(accounts, "22222222")
    assert selected == [{"accountNumber": "22222222", "hashValue": "h2"}]


@pytest.mark.unit
def test_match_account_explicit_mismatch_exits() -> None:
    module = _load_cli_module()
    accounts = [
        {"accountNumber": "11111111", "hashValue": "h1"},
        {"accountNumber": "22222222", "hashValue": "h2"},
    ]

    with pytest.raises(SystemExit) as exc_info:
        module._match_account(accounts, "99999999")
    assert exc_info.value.code != 0


@pytest.mark.unit
def test_match_account_multiple_without_filter_exits() -> None:
    module = _load_cli_module()
    accounts = [
        {"accountNumber": "11111111", "hashValue": "h1"},
        {"accountNumber": "22222222", "hashValue": "h2"},
    ]

    with pytest.raises(SystemExit) as exc_info:
        module._match_account(accounts, None)
    assert exc_info.value.code != 0


@pytest.mark.unit
def test_match_account_empty_exits() -> None:
    module = _load_cli_module()

    with pytest.raises(SystemExit):
        module._match_account([], None)
