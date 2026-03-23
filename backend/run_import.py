"""
Direct import script — runs inside the backend container at /app/.
Calls ImportService.import_file() directly for user fscheffold.
Pass filenames as args, or it imports all four files in order.
"""

import asyncio
import sys
from pathlib import Path

import os

os.environ.setdefault("UPLOAD_DIR", "/app/uploads")

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.config import settings
from app.repositories.trade_repository import TradeRepository
from app.services.import_service import ImportService
from app.models.user import User
from sqlalchemy import select
import uuid as _uuid

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
    engine = create_async_engine(settings.database_url, echo=False)
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
            import_result = await svc.import_file(
                content=xml_bytes,
                filename=xml_file.name,
                broker="ibkr_flex",
                account_id=account_id,
                user_id=user.id,
            )
            await session.commit()

            open_lots_after = await trade_repo.list_open_lots_by_user(user.id)
            print(
                f"  created={import_result.trades_created}  skipped={import_result.trades_skipped}  open_after={len(open_lots_after)}"
            )
            if import_result.warnings:
                for w in import_result.warnings:
                    print(f"  WARN: {w}")

    await engine.dispose()
    print("\nDone.")


asyncio.run(main())
