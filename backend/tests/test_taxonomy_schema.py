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

"""Unit tests for taxonomy schema validation."""

import pytest
from pydantic import ValidationError

from app.schemas.taxonomy import TaxonomyCreate, TaxonomyUpdate


@pytest.mark.unit
def test_hex_color_accepts_valid_format() -> None:
    payload = TaxonomyCreate(name="Setup", scope="trades", color_hex="#A3F4B1")
    assert payload.color_hex == "#A3F4B1"


@pytest.mark.unit
def test_hex_color_rejects_short_format() -> None:
    with pytest.raises(ValidationError):
        TaxonomyCreate(name="Setup", scope="trades", color_hex="#FFF")


@pytest.mark.unit
def test_hex_color_rejects_missing_hash() -> None:
    with pytest.raises(ValidationError):
        TaxonomyCreate(name="Setup", scope="trades", color_hex="A3F4B1")


@pytest.mark.unit
def test_taxonomy_update_hex_validator_rejects_invalid() -> None:
    with pytest.raises(ValidationError):
        TaxonomyUpdate(color_hex="#123")
