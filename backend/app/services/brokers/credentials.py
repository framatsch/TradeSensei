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

"""Decryption helpers for broker credentials stored as account properties."""

import uuid

from app.core.exceptions import ConfigurationError
from app.models.account import Account
from app.models.account_property import AccountProperty
from app.utils.encryption import decrypt_token


def get_property(account: Account, key: str) -> str:
    """Retrieve and decrypt a named property from the account.

    Raises:
        ConfigurationError: If the key is missing or decryption fails.
    """
    prop: AccountProperty | None = next((p for p in account.properties if p.key == key), None)
    if prop is None:
        raise ConfigurationError(f"Missing account property: {key}")
    try:
        return decrypt_token(prop.value)
    except Exception as exc:
        raise ConfigurationError(f"Failed to decrypt property {key}.") from exc


def resolve_property(provided: dict[str, str], account: Account | None, keys: tuple[str, ...]) -> str:
    """Return the first non-blank provided value, else the first stored property.

    Raises:
        ConfigurationError: If no value is found or decryption fails.
    """
    for key in keys:
        value = provided.get(key)
        if value is not None and value.strip() != "":
            return value.strip()

    if account is not None:
        for key in keys:
            prop: AccountProperty | None = next(
                (p for p in account.properties if p.key == key),
                None,
            )
            if prop is None:
                continue
            try:
                return decrypt_token(prop.value)
            except Exception as exc:
                raise ConfigurationError(f"Failed to decrypt property {key}.") from exc

    raise ConfigurationError(f"Missing account property: {keys[0]}")


def resolve_optional_property(account: Account, keys: tuple[str, ...]) -> str | None:
    """Return the first stored property among ``keys``, or ``None``.

    Raises:
        ConfigurationError: If decryption fails.
    """
    for key in keys:
        prop: AccountProperty | None = next((p for p in account.properties if p.key == key), None)
        if prop is None:
            continue
        try:
            return decrypt_token(prop.value)
        except Exception as exc:
            raise ConfigurationError(f"Failed to decrypt property {key}.") from exc
    return None


def require_portfolio_id(account: Account) -> uuid.UUID:
    """Return the account's portfolio ID.

    Raises:
        ConfigurationError: If the account is not linked to a portfolio.
    """
    if account.portfolio_id is None:
        raise ConfigurationError(f"Account {account.id} is not linked to a portfolio.")
    return account.portfolio_id
