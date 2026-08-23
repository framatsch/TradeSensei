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

"""
Direct import script — runs inside the backend container at /app/.
Calls ImportService.import_trades() directly for user fscheffold.
Pass filenames as args, or it imports all four files in order.
"""

import asyncio
import os
import sys
from pathlib import Path

os.environ.setdefault("UPLOAD_DIR", "/app/uploads")

import uuid as _uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.user import User
from app.repositories.trade_repository import TradeRepository
from app.services.import_service import ImportService

USERNAME = "fscheffold"
IBKR_ACCOUNT_ID_STR = "47a7305b-061b-43e9-8aea-848c4fadd62d"

FILES = (
    sys.argv[1:]
    if len(sys.argv) > 1
    else [
        "/app/TraderJournal_2023.xml",
        "/app/TraderJournal_2024.xml",
        "/app/TraderJournal_2025.xml",
        "/app/TraderJournal_Q1_2026.xml",
    ]
)


async def main() -> None:
    engine = create_async_engine(settings.async_database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        result = await session.execute(select(User).where(User.username == USERNAME))
        user = result.scalar_one_or_none()
        if user is None:
            print(f"ERROR: user '{USERNAME}' not found")
            return
        print(f"User: {user.username}  id={user.id}")

        account_id = _uuid.UUID(IBKR_ACCOUNT_ID_STR)

        for file_path in FILES:
            xml_file = Path(file_path)
            if not xml_file.exists():
                print(f"SKIP (not found): {xml_file}")
                continue

            trade_repo = TradeRepository(session)
            open_lots = await trade_repo.list_open_lots_by_user(user.id)
            print(f"\n[{xml_file.name}] Open lots before: {len(open_lots)}")

            svc = ImportService(session)
            xml_bytes = xml_file.read_bytes()
            import_result = await svc.import_trades(
                content=xml_bytes,
                filename=xml_file.name,
                broker="ibkr",
                account_id=account_id,
                user_id=user.id,
            )
            await session.commit()

            open_lots_after = await trade_repo.list_open_lots_by_user(user.id)
            print(
                f"  created={import_result.trades_created} "
                f"skipped={import_result.trades_skipped} "
                f"open_after={len(open_lots_after)}"
            )
            if import_result.warnings:
                for w in import_result.warnings:
                    print(f"  WARN: {w}")

    await engine.dispose()
    print("\nDone.")


asyncio.run(main())
