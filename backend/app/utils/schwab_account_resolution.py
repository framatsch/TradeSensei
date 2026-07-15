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

from __future__ import annotations

from app.core.exceptions import ImportAccountMismatchError, ImportParseError


def resolve_schwab_account_entry(
    *,
    accounts: list[dict[str, object]],
    configured_account_number: str | None,
    context: str,
) -> tuple[dict[str, object], str | None]:
    """Resolve one Schwab account entry by configured account number.

    Returns the selected account entry and, when auto-binding is applicable,
    the account number that should be persisted.
    """
    if not accounts:
        raise ImportParseError("Schwab payload must include at least one account entry.")

    file_numbers = [str(entry.get("accountNumber", "")).strip() for entry in accounts]
    non_empty_numbers = [number for number in file_numbers if number]

    configured_number = (configured_account_number or "").strip()
    if configured_number:
        for entry in accounts:
            if str(entry.get("accountNumber", "")).strip() == configured_number:
                return entry, configured_number
        available = ", ".join(non_empty_numbers) if non_empty_numbers else "<none>"
        raise ImportAccountMismatchError(
            f"Schwab account mismatch: configured account number '{configured_number}' "
            f"is not present in broker accounts [{available}]."
        )

    if len(accounts) == 1:
        selected_number = str(accounts[0].get("accountNumber", "")).strip() or None
        if selected_number is None:
            raise ImportParseError("Schwab account entry is missing required field 'accountNumber'.")
        return accounts[0], selected_number

    available = ", ".join(non_empty_numbers) if non_empty_numbers else "<none>"
    if context == "sync":
        raise ImportAccountMismatchError(
            "multiple Schwab accounts found - enter account number; "
            f"available account numbers: [{available}]"
        )

    raise ImportAccountMismatchError(
        "Schwab account is not configured and file is ambiguous; "
        f"available account numbers: [{available}]."
    )
