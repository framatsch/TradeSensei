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

"""Pure, lossless decoding of JSON and execution CSV files."""

import csv
import io
import json
import re
from decimal import Decimal


class GenericLoadError(ValueError):
    """Safe file-decoding failure with an optional data-row location."""

    def __init__(self, code: str, field: str = "file", row: int | None = None) -> None:
        """Store only a code and location, never source values."""
        super().__init__("Invalid execution file")
        self.code = code
        self.field = field
        self.row = row


def _invalid_constant(value: str) -> object:
    del value
    raise GenericLoadError("invalid_number")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise GenericLoadError("duplicate_json_key")
        result[key] = value
    return result


def load_json(content: bytes) -> object:
    """Decode JSON without binary floating-point or duplicate object keys."""
    try:
        result: object = json.loads(
            content.decode("utf-8-sig"),
            parse_float=Decimal,
            parse_int=int,
            parse_constant=_invalid_constant,
            object_pairs_hook=_unique_object,
        )
        return result
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise GenericLoadError("invalid_json") from exc


def load_csv(content: bytes, columns: list[str], required: set[str], numeric: set[str]) -> list[dict[str, object]]:
    """Decode strict headered CSV with flattened option fields.

    Args:
        content: UTF-8 CSV bytes, optionally with a BOM.
        columns: Allowed column names derived from the format models.
        required: Required execution columns.
        numeric: Decimal column names requiring locale-neutral syntax.

    Returns:
        Execution dictionaries with option fields nested.
    """
    try:
        reader = csv.reader(io.StringIO(content.decode("utf-8-sig"), newline=""), strict=True)
        header = next(reader, [])
        if not header or len(set(header)) != len(header) or not required.issubset(header):
            raise GenericLoadError("invalid_header")
        if any(column not in columns for column in header):
            raise GenericLoadError("unknown_column")
        rows: list[dict[str, object]] = []
        for index, cells in enumerate(reader, start=1):
            if len(cells) != len(header):
                raise GenericLoadError("column_count", row=index)
            row: dict[str, object] = {}
            option: dict[str, object] = {}
            for column, cell in zip(header, cells, strict=True):
                cell = cell.strip()
                if not cell:
                    continue
                value: object = cell
                if column in numeric:
                    if re.fullmatch(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)", cell) is None:
                        raise GenericLoadError("invalid_number", column, index)
                    value = Decimal(cell)
                if column == "multiplier":
                    if re.fullmatch(r"[0-9]+", cell) is None:
                        raise GenericLoadError("invalid_integer", column, index)
                    value = int(cell)
                if column.startswith("option_"):
                    option[column.removeprefix("option_")] = value
                else:
                    row[column] = value
            if option:
                row["option"] = option
            rows.append(row)
        return rows
    except (UnicodeError, csv.Error, ValueError) as exc:
        if isinstance(exc, GenericLoadError):
            raise
        raise GenericLoadError("invalid_csv") from exc
