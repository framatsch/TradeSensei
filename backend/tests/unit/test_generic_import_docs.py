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

"""Keep the format guide's published examples aligned with the generic adapter."""

import csv
import io
import re
from pathlib import Path

import pytest

from app.services.brokers.contracts import BrokerType
from app.services.brokers.generic.validation import csv_columns, parse_document
from app.services.brokers.registry import get_adapter
from app.services.generic_format_service import GenericFormatService
from tests.utils.generic_import import broker_fixture_to_generic_csv

pytestmark = pytest.mark.unit

_GUIDE = Path(__file__).resolve().parents[3] / "docs" / "import-generic-format.md"
_MANUAL_CSV_DIR = Path(__file__).resolve().parents[3] / "tests" / "test_data" / "generic"


def test_guide_json_and_csv_examples_validate_and_are_equivalent() -> None:
    """Every published execution example must parse and describe the same fills."""
    guide = _GUIDE.read_text(encoding="utf-8")
    importer = get_adapter(BrokerType.GENERIC).file_import
    assert importer is not None
    examples = {}
    for extension in ("json", "csv"):
        blocks = re.findall(rf"```{extension}\n(.*?)\n```", guide, flags=re.DOTALL)
        assert blocks, f"Guide lacks a {extension} example."
        batches = [importer.parse(block.encode("utf-8"), f"guide.{extension}") for block in blocks]
        assert all(batch.executions and not batch.warnings for batch in batches)
        examples[extension] = [raw.model_dump(exclude={"raw_data"}) for batch in batches for raw in batch.executions]
    assert examples["json"] == examples["csv"]


def test_generated_csv_template_model_derived_header_and_examples_validate() -> None:
    content = GenericFormatService().template()
    rows = list(csv.reader(io.StringIO(content.decode())))
    assert rows[0] == csv_columns()
    assert len(rows) == 3
    parsed = parse_document(content, "template.csv")
    assert len(parsed.executions) == 2
    assert [row.side for row in parsed.executions] == ["BUY", "SELL"]


@pytest.mark.parametrize(
    ("broker", "source_name", "count"),
    [
        ("ibkr", "TraderJournal_anonymized_combined.xml", 339),
        ("ibkr", "combo_positions.xml", 16),
        ("schwab", "schwab_aggregation.json", 7),
        ("schwab", "schwab_short_roundtrip.json", 2),
        ("schwab", "schwab_transactions_real_trimmed.json", 5),
    ],
)
def test_manual_csv_examples_match_native_source(broker: str, source_name: str, count: int) -> None:
    importer = get_adapter(BrokerType.GENERIC).file_import
    assert importer is not None
    source = _MANUAL_CSV_DIR.parent / broker / source_name
    fixture = _MANUAL_CSV_DIR / broker / f"{source.stem}.csv"
    content = fixture.read_bytes()
    assert content == broker_fixture_to_generic_csv(source.read_bytes(), source.name, broker)
    document = parse_document(content, fixture.name)
    assert len(document.executions) == count
    assert all(row.external_id is not None for row in document.executions)
    batch = importer.parse(content, fixture.name)
    assert len(batch.executions) == count
    assert not batch.warnings
