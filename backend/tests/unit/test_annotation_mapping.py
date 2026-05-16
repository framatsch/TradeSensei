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

"""Unit tests for annotation value-to-column mapping utility."""

from decimal import Decimal

import pytest

from app.utils.annotation_mapping import map_value_to_column


def test_map_int_value() -> None:
    mapped = map_value_to_column("int", 3, None)
    assert mapped == {
        "value_int": 3,
        "value_float": None,
        "value_bool": None,
        "value_string": None,
    }


def test_map_float_value() -> None:
    mapped = map_value_to_column("float", 1.5, None)
    assert mapped == {
        "value_int": None,
        "value_float": Decimal("1.5"),
        "value_bool": None,
        "value_string": None,
    }


def test_map_bool_value() -> None:
    mapped = map_value_to_column("bool", False, None)
    assert mapped == {
        "value_int": None,
        "value_float": None,
        "value_bool": False,
        "value_string": None,
    }


def test_map_string_enum_value() -> None:
    mapped = map_value_to_column(
        "string_enum",
        "Medium",
        {"options": ["Low", "Medium", "High"]},
    )
    assert mapped == {
        "value_int": None,
        "value_float": None,
        "value_bool": None,
        "value_string": "Medium",
    }


def test_reject_wrong_type() -> None:
    with pytest.raises(ValueError):
        map_value_to_column("int", "3", None)


def test_reject_out_of_range() -> None:
    with pytest.raises(ValueError):
        map_value_to_column("float", 11.0, {"min": 1, "max": 10})


def test_reject_invalid_enum_option() -> None:
    with pytest.raises(ValueError):
        map_value_to_column(
            "string_enum",
            "Critical",
            {"options": ["Low", "Medium", "High"]},
        )
