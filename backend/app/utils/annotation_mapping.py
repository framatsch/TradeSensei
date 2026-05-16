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

"""Helpers for mapping raw annotation values into typed DB columns."""

from decimal import Decimal
from typing import Any


def _base_mapping() -> dict[str, Any]:
    return {
        "value_int": None,
        "value_float": None,
        "value_bool": None,
        "value_string": None,
    }


def _validate_range(value: int | float | Decimal, scale_labels: dict[str, Any] | None) -> None:
    if not isinstance(scale_labels, dict):
        return
    min_value = scale_labels.get("min")
    max_value = scale_labels.get("max")
    if min_value is not None and value < min_value:
        raise ValueError("value is below allowed minimum")
    if max_value is not None and value > max_value:
        raise ValueError("value is above allowed maximum")


def map_value_to_column(
    annotation_type: str,
    value: Any,
    scale_labels: dict[str, Any] | None,
) -> dict[str, Any]:
    """Map a raw value to exactly one typed annotation column.

    Raises:
        ValueError: If value does not match the requested type or constraints.
    """
    mapped = _base_mapping()

    if annotation_type == "int":
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("int annotation requires integer value")
        _validate_range(value, scale_labels)
        mapped["value_int"] = value
        return mapped

    if annotation_type == "float":
        if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
            raise ValueError("float annotation requires numeric value")
        numeric_value = float(value)
        _validate_range(numeric_value, scale_labels)
        mapped["value_float"] = Decimal(str(value))
        return mapped

    if annotation_type == "bool":
        if not isinstance(value, bool):
            raise ValueError("bool annotation requires boolean value")
        mapped["value_bool"] = value
        return mapped

    if annotation_type == "string_enum":
        if not isinstance(value, str):
            raise ValueError("string_enum annotation requires string value")
        if not isinstance(scale_labels, dict) or not isinstance(scale_labels.get("options"), list):
            raise ValueError("string_enum annotation requires scale_labels.options")
        options = scale_labels["options"]
        if value not in options:
            raise ValueError("value is not in allowed enum options")
        mapped["value_string"] = value
        return mapped

    raise ValueError("unsupported annotation type")
