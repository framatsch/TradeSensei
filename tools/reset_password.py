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
"""CLI tool to reset a user's password in the database."""

import argparse
import asyncio
import sys
import os

# Wir fangen fehlende Env-Vars ab und setzen Fallbacks (besonders fuer secret_key),
# bevor wir Pydantic's Settings laden
if not os.getenv("SECRET_KEY"):
    os.environ["SECRET_KEY"] = (
        "dummy_secret_key_nur_fuer_passwort_tool_gebraucht_damit_pydantic_nicht_crasht_12345"
    )

if not os.getenv("DATABASE_URL") and not os.getenv("DB_USER"):
    print("Warnung: DATABASE_URL oder DB_USER nicht in Umgebungsvariablen gefunden.")
    print(
        "Versuche lokal (postgresql+asyncpg://tradesensei:tradesensei@localhost:5432/tradesensei) zu verbinden..."
    )
    os.environ["DATABASE_URL"] = (
        "postgresql+asyncpg://tradesensei:tradesensei@localhost:5432/tradesensei"
    )

# Workaround für passlib Issue mit bcrypt >= 4.0.0
try:
    import bcrypt

    if not hasattr(bcrypt, "__about__"):

        class _About:
            __version__ = getattr(bcrypt, "__version__", "4.0.0")

        bcrypt.__about__ = _About()
except ImportError:
    pass

# Füge das backend-Verzeichnis in den Pfad ein, damit 'app' gefunden wird,
# wenn das Skript aus dem Root-Verzeichnis ausgeführt wird.
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
)

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Setze das Passwort eines Benutzers manuell über die Datenbank zurück.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="Beispiele:\n"
        "  uv run python reset_password.py -u testuser -p NeuesPasswort123!\n"
        "  uv run python reset_password.py -e test@example.com -p NeuesPasswort123!",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-u", "--username", help="Der Benutzername des Kontos")
    group.add_argument("-e", "--email", help="Die E-Mail-Adresse des Kontos")
    parser.add_argument(
        "-p", "--password", required=True, help="Das neue Passwort als String"
    )

    args = parser.parse_args()

    # Verbindung zur Datenbank herstellen
    try:
        engine = create_async_engine(settings.async_database_url)
        async_session = async_sessionmaker(engine, expire_on_commit=False)
    except Exception as e:
        print(f"Fehler beim Verbinden mit der Datenbank: {e}", file=sys.stderr)
        print(
            "Bitte setze DATABASE_URL (z.B. DATABASE_URL=postgresql+asyncpg://user:pass@host/db uv run ...)",
            file=sys.stderr,
        )
        sys.exit(1)

    # Das hashen aufrufen
    new_hash = hash_password(args.password)

    try:
        async with async_session() as session:
            if args.username:
                stmt = select(User).where(User.username == args.username)
                identifier = f"Benutzername '{args.username}'"
            else:
                stmt = select(User).where(User.email == args.email)
                identifier = f"E-Mail-Adresse '{args.email}'"

            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                print(
                    f"❌ Fehler: Es konnte kein Benutzer mit {identifier} gefunden werden.",
                    file=sys.stderr,
                )
                await engine.dispose()
                sys.exit(1)

            # Passwort aktualisieren und Tokens zurücksetzen
            user.hashed_password = new_hash
            user.refresh_token_version += 1

            session.add(user)
            await session.commit()

            print(
                f"✅ Erfolg: Das Passwort für '{user.username}' ({user.email}) wurde erfolgreich zurückgesetzt."
            )
    except Exception as e:
        print(f"❌ Ein unerwarteter Fehler ist aufgetreten: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
