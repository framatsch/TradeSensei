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

"""Check fixture conversion and generic canonical mapping against native IBKR."""

from pathlib import Path

import pytest

from app.services.brokers.contracts import BrokerType
from app.services.brokers.registry import get_adapter
from app.utils.parsers.ibkr_xml import IBKRXMLParser
from tests.utils.generic_import import ibkr_fixture_to_generic

pytestmark = pytest.mark.unit

_FIXTURES = sorted((Path(__file__).resolve().parents[1] / "fixtures" / "ibkr").glob("*.xml"))


@pytest.mark.parametrize("fixture", _FIXTURES, ids=lambda path: path.name)
@pytest.mark.parametrize("external_ids", [True, False], ids=["external-id", "fingerprint"])
def test_converted_fixtures_preserve_canonical_mapping(fixture: Path, external_ids: bool) -> None:
    """Preserve all execution economics, contract details, flip markers, and splits."""
    content = fixture.read_bytes()
    native, actions = IBKRXMLParser().parse_raw(content, fixture.name)
    importer = get_adapter(BrokerType.GENERIC).file_import
    assert importer is not None
    generic = importer.parse(ibkr_fixture_to_generic(content, fixture.name, external_ids=external_ids), "fixture.json")
    assert len(native) == len(generic.executions)
    # Native empty order IDs normalize to absent in the public format. Cash
    # metadata is required only for grouped orders; broker/identity/raw payload
    # fields deliberately differ between representations.
    excluded = {"id", "broker_type", "raw_data", "net_cash", "order_id"}
    for native_raw, generic_raw in zip(native, generic.executions, strict=True):
        assert native_raw.model_dump(exclude=excluded) == generic_raw.model_dump(exclude=excluded)
        assert (native_raw.order_id or None) == generic_raw.order_id
        if native_raw.order_id and native_raw.net_cash is not None:
            assert native_raw.net_cash == generic_raw.net_cash
    assert actions == generic.corporate_actions
