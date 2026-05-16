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

"""Unit tests for personal access token helpers in app.core.security."""

import hashlib

import pytest

from app.core.security import generate_pat, hash_pat


@pytest.mark.unit
def test_hash_pat_matches_sha256_hex_digest() -> None:
    token = "example-personal-access-token"
    expected = hashlib.sha256(token.encode()).hexdigest()
    assert hash_pat(token) == expected


@pytest.mark.unit
def test_hash_pat_is_deterministic() -> None:
    token = "deterministic-token"
    assert hash_pat(token) == hash_pat(token)


@pytest.mark.unit
def test_generate_pat_returns_unique_tokens() -> None:
    token_a = generate_pat()
    token_b = generate_pat()

    assert isinstance(token_a, str)
    assert isinstance(token_b, str)
    assert token_a
    assert token_b
    assert token_a != token_b
