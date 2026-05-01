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
