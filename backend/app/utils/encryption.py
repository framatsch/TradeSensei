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

"""Fernet-based symmetric encryption utilities for sensitive token storage.

Provides :func:`encrypt_token` and :func:`decrypt_token` which wrap the
``cryptography`` library's ``Fernet`` cipher.  The encryption key is read
from :attr:`~app.core.config.Settings.broker_encryption_key`.
"""

from cryptography.fernet import Fernet

from app.core.config import settings
from app.core.exceptions import ConfigurationError

_fernet_instance: Fernet | None = None


def _get_fernet() -> Fernet:
    """Return a cached :class:`~cryptography.fernet.Fernet` instance.

    The instance is constructed lazily the first time it is needed, using
    ``settings.broker_encryption_key`` as the key material.

    Returns:
        A ready-to-use :class:`~cryptography.fernet.Fernet` cipher.

    Raises:
        :class:`~app.core.exceptions.ConfigurationError`: If
            ``broker_encryption_key`` is not set in the application settings.
    """
    global _fernet_instance
    if _fernet_instance is None:
        key = settings.broker_encryption_key
        if not key:
            raise ConfigurationError(
                "BROKER_ENCRYPTION_KEY is not configured. "
                "Generate a key with: python -c "
                '"from cryptography.fernet import Fernet; '
                'print(Fernet.generate_key().decode())"'
            )
        _fernet_instance = Fernet(key.encode())
    return _fernet_instance


def encrypt_token(plaintext: str) -> str:
    """Encrypt a plaintext token using Fernet symmetric encryption.

    The result is a URL-safe base-64 encoded ciphertext string that can be
    safely stored in the database.

    Args:
        plaintext: The raw token string to encrypt.

    Returns:
        A Fernet-encrypted, base-64 encoded ciphertext string.

    Raises:
        :class:`~app.core.exceptions.ConfigurationError`: If the encryption
            key is not configured.
    """
    fernet = _get_fernet()
    return fernet.encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    """Decrypt a Fernet-encrypted token back to plaintext.

    Args:
        ciphertext: A Fernet-encrypted, base-64 encoded token string as
            produced by :func:`encrypt_token`.

    Returns:
        The original plaintext token string.

    Raises:
        :class:`~app.core.exceptions.ConfigurationError`: If the encryption
            key is not configured.
        :class:`~cryptography.fernet.InvalidToken`: If the ciphertext is
            tampered with or was encrypted with a different key.
    """
    fernet = _get_fernet()
    return fernet.decrypt(ciphertext.encode()).decode()
