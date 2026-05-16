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

#!/usr/bin/env python3
"""Standalone CLI script to reset a user's password directly via the database.

Usage examples::

    # Interactive (recommended):
    uv run python backend/reset_password.py -u admin
    uv run python backend/reset_password.py -e user@example.com

    # Non-interactive (piped password, useful in scripts):
    echo "newpassword" | uv run python backend/reset_password.py -u admin

This script must be run from the project root so that the ``backend/``
directory is on the Python path and the app modules can be imported.
"""

import argparse
import asyncio
import os
import sys
import types

# ---------------------------------------------------------------------------
# Monkeypatch: passlib + bcrypt >= 4.x compatibility
# ---------------------------------------------------------------------------
# passlib 1.7.x tries to read ``bcrypt.__about__.__version__``, which was
# removed in bcrypt 4.0.  Inject a stub module so the import does not crash.
import bcrypt  # noqa: E402 – must come before passlib is touched

if not hasattr(bcrypt, "__about__"):
    _about_stub = types.ModuleType("bcrypt.__about__")
    _about_stub.__version__ = getattr(bcrypt, "__version__", "4.0.0")  # type: ignore[attr-defined]
    bcrypt.__about__ = _about_stub  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# Environment variable fallbacks
# ---------------------------------------------------------------------------
# Must happen BEFORE importing app.core.config so pydantic-settings picks
# up the env vars when the Settings object is constructed at import time.

_DEFAULT_DB_URL = "postgresql+asyncpg://tradesensei:tradesensei@localhost:5432/tradesensei"

if not os.environ.get("SECRET_KEY"):
    # Password hashing does not require the real secret key; only JWT
    # signing does.  We use a dummy value so that Settings validates.
    os.environ["SECRET_KEY"] = "cli-dummy-secret-key-not-used-for-hashing-xXxXx"

if not os.environ.get("DATABASE_URL") and not (
    os.environ.get("DB_USER") and os.environ.get("DB_PASSWORD")
):
    print(
        "WARNING: DATABASE_URL is not set. "
        f"Falling back to default local connection: {_DEFAULT_DB_URL}",
        file=sys.stderr,
    )
    os.environ["DATABASE_URL"] = _DEFAULT_DB_URL

# ---------------------------------------------------------------------------
# Add backend/ to sys.path so ``app.*`` imports resolve correctly
# ---------------------------------------------------------------------------

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

# ---------------------------------------------------------------------------
# App imports (after env + path setup)
# ---------------------------------------------------------------------------

from sqlalchemy import select, text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.user import User  # noqa: E402

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Construct and return the argument parser for this CLI tool.

    Returns:
        A configured :class:`argparse.ArgumentParser` instance.
    """
    parser = argparse.ArgumentParser(
        prog="reset_password",
        description="Reset a user's password directly in the database.",
        epilog=(
            "The new password is read interactively via a secure prompt "
            "(getpass) when running in a terminal, or from stdin when piped. "
            "The user's active sessions are invalidated by incrementing the "
            "refresh_token_version. "
            "Run from the project root: "
            "uv run python backend/reset_password.py -u <username>"
        ),
    )
    lookup_group = parser.add_mutually_exclusive_group(required=True)
    lookup_group.add_argument(
        "-u",
        "--username",
        metavar="USERNAME",
        help="Username of the account whose password should be reset.",
    )
    lookup_group.add_argument(
        "-e",
        "--email",
        metavar="EMAIL",
        help="Email address of the account whose password should be reset.",
    )
    return parser


# ---------------------------------------------------------------------------
# Password input
# ---------------------------------------------------------------------------


def _read_password() -> str:
    """Read and confirm the new password from the user.

    When running in an interactive terminal, uses :func:`getpass.getpass`
    so the password is not echoed.  When stdin is piped (non-interactive),
    reads a single line from stdin (no confirmation required).

    Returns:
        The plain-text password string entered by the user.
    """
    if sys.stdin.isatty():
        import getpass

        password = getpass.getpass("New password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Error: Passwords do not match.", file=sys.stderr)
            sys.exit(1)
        if not password:
            print("Error: Password must not be empty.", file=sys.stderr)
            sys.exit(1)
        return password
    else:
        # Non-interactive mode: read one line from stdin (no confirmation).
        password = sys.stdin.readline().rstrip("\n")
        if not password:
            print("Error: Password must not be empty.", file=sys.stderr)
            sys.exit(1)
        return password


# ---------------------------------------------------------------------------
# Core async logic
# ---------------------------------------------------------------------------


async def _reset_password(
    *,
    username: str | None,
    email: str | None,
    new_password: str,
) -> None:
    """Look up the user and update their hashed password in the database.

    Creates its own engine and session to avoid depending on the FastAPI
    lifespan or the module-level engine defined in ``app.core.database``.

    Args:
        username: Username to look up (mutually exclusive with ``email``).
        email: Email address to look up (mutually exclusive with ``username``).
        new_password: Plain-text password to hash and store.

    Raises:
        SystemExit: If the user is not found in the database.
    """
    engine = create_async_engine(
        settings.async_database_url,
        echo=False,
        pool_pre_ping=True,
    )
    session_factory = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )

    try:
        async with session_factory() as session:
            # Disable RLS for this admin session so the script works
            # even when connected as a role without BYPASSRLS.
            await session.execute(text("SET row_security = off"))

            # Build the lookup query based on which flag was provided.
            if username is not None:
                stmt = select(User).where(User.username == username)
                identifier = f"username={username!r}"
            else:
                stmt = select(User).where(User.email == email)
                identifier = f"email={email!r}"

            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if user is None:
                print(
                    f"Error: No user found with {identifier}.",
                    file=sys.stderr,
                )
                sys.exit(1)

            # Hash and apply the new password; invalidate existing sessions.
            user.hashed_password = hash_password(new_password)
            user.refresh_token_version += 1

            await session.commit()

        print(
            f"Password for user {user.username!r} has been reset successfully. "
            "All existing sessions have been invalidated."
        )
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse arguments, collect the new password, and run the reset.

    This is the top-level entry point invoked when the script is executed
    directly.
    """
    parser = _build_parser()
    args = parser.parse_args()

    new_password = _read_password()

    asyncio.run(
        _reset_password(
            username=args.username,
            email=args.email,
            new_password=new_password,
        )
    )


if __name__ == "__main__":
    main()
