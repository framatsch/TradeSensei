"""Unit tests for the Fernet-based token encryption utilities.

Tests cover the encrypt/decrypt roundtrip, the missing-key error path, and
the tampered-ciphertext error path.  All tests reset the module-level
Fernet singleton so they do not interfere with each other.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet, InvalidToken

import app.utils.encryption as enc_module
from app.core.exceptions import ConfigurationError


@pytest.fixture(autouse=True)
def reset_fernet_singleton() -> None:
    """Reset the module-level Fernet singleton before every test.

    Ensures that a key set in one test does not leak into the next.
    """
    enc_module._fernet_instance = None
    yield  # type: ignore[misc]
    enc_module._fernet_instance = None


def _fresh_key() -> str:
    """Generate a fresh Fernet key string for test use.

    Returns:
        A URL-safe base-64 encoded 32-byte Fernet key as a ``str``.
    """
    return Fernet.generate_key().decode()


async def test_encrypt_decrypt_roundtrip() -> None:
    """encrypt_token followed by decrypt_token returns the original plaintext.

    Uses a freshly generated Fernet key so the test is self-contained and
    does not depend on any environment variable.
    """
    key = _fresh_key()
    with patch.object(enc_module.settings, "broker_encryption_key", key):
        ciphertext = enc_module.encrypt_token("my-secret-access-token")
        assert ciphertext != "my-secret-access-token"

        plaintext = enc_module.decrypt_token(ciphertext)
        assert plaintext == "my-secret-access-token"


async def test_encrypt_raises_if_no_key() -> None:
    """encrypt_token raises ConfigurationError when broker_encryption_key is None.

    Simulates a deployment where the ``BROKER_ENCRYPTION_KEY`` environment
    variable has not been set.
    """
    with patch.object(enc_module.settings, "broker_encryption_key", None):
        with pytest.raises(ConfigurationError, match="BROKER_ENCRYPTION_KEY"):
            enc_module.encrypt_token("token")


async def test_decrypt_raises_on_invalid_token() -> None:
    """decrypt_token raises InvalidToken when the ciphertext is tampered.

    Encrypts with a valid key, then attempts to decrypt a corrupted version
    of the ciphertext.
    """
    key = _fresh_key()
    with patch.object(enc_module.settings, "broker_encryption_key", key):
        ciphertext = enc_module.encrypt_token("original")

    # Reset singleton so decrypt uses the same key
    enc_module._fernet_instance = None
    with patch.object(enc_module.settings, "broker_encryption_key", key):
        with pytest.raises(InvalidToken):
            enc_module.decrypt_token(ciphertext[:-4] + "XXXX")
