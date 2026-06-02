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

"""Test migration e6c9b3f1a2d0 (URL to storage ref backfill)."""

import uuid
from datetime import datetime, timezone
import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from alembic.config import Config
from alembic import command
from app.core.config import settings

# Run this test serially to avoid messing with other tests' schemas.
@pytest.mark.integration
async def test_migration_roundtrip(engine):
    """Test the e6c9b3f1a2d0 migration upgrades and downgrades URLs correctly."""
    alembic_cfg = Config("alembic.ini")
    
    # 1. Downgrade to just before this migration
    # Note: Alembic commands are synchronous, so we run them in a thread if needed,
    # but here we can just call them directly as they use their own sync engine,
    # or we might need to run them synchronously.
    
    # Alembic uses sync engine by default in migrations, let's see if we can run it.
    import asyncio
    def run_alembic(cmd, *args):
        getattr(command, cmd)(alembic_cfg, *args)
        
    await asyncio.to_thread(run_alembic, "downgrade", "314159265358")
    
    public_url = settings.storage_public_url.rstrip("/")
    
    # 2. Insert test data (simulating state before migration)
    async with engine.begin() as conn:
        # Create users, portfolios, accounts
        user_id = uuid.uuid4()
        portfolio_id = uuid.uuid4()
        account_id = uuid.uuid4()
        trade_id = uuid.uuid4()
        checkin_id = uuid.uuid4()
        playbook_id = uuid.uuid4()
        attachment_id = uuid.uuid4()
        
        await conn.execute(sa.text("INSERT INTO users (id, username, email, hashed_password, created_at, updated_at) VALUES (:id, 'mig_test', :email, :pw, :ts, :ts)"), {"id": user_id, "email": "mig_test@example.com", "pw": "hash", "ts": datetime.now(timezone.utc)})
        await conn.execute(sa.text("INSERT INTO portfolios (id, user_id, name, base_currency, created_at, updated_at) VALUES (:id, :uid, 'Mig', 'USD', :ts, :ts)"), {"id": portfolio_id, "uid": user_id, "ts": datetime.now(timezone.utc)})
        await conn.execute(sa.text("INSERT INTO accounts (id, portfolio_id, user_id, name, type, created_at, updated_at) VALUES (:id, :pid, :uid, 'Mig', 'manual', :ts, :ts)"), {"id": account_id, "pid": portfolio_id, "uid": user_id, "ts": datetime.now(timezone.utc)})
        
        # Insert checkin with text array
        await conn.execute(sa.text("INSERT INTO daily_checkins (id, user_id, date, market_phase, notes, news_links, custom_metrics, screenshot_urls, created_at, updated_at) VALUES (:id, :uid, '2023-01-01', 'BULL', '', '{}', '{}', :urls, :ts, :ts)"), {
            "id": checkin_id, "uid": user_id, "urls": [f"{public_url}/bucket/checkins/img1.png", "https://other.com/img.png", ""], "ts": datetime.now(timezone.utc)
        })
        
        # Insert trade with JSONB array
        import json
        await conn.execute(sa.text("INSERT INTO trades (id, user_id, account_id, position_id, direction, symbol, asset_class, quantity, entry_price, opened_at, commission, notes, image_urls, is_combo, created_at, updated_at) VALUES (:id, :uid, :aid, :id, 'LONG', 'AAPL', 'EQUITY', 10, 100, :ts, 0, '', :urls, false, :ts, :ts)"), {
                "id": trade_id, "uid": user_id, "aid": account_id, "urls": json.dumps([f"{public_url}/bucket/trades/img2.png"]), "ts": datetime.now(timezone.utc)
            })
        
        # Insert playbook attachment
        await conn.execute(sa.text("INSERT INTO playbooks (id, user_id, name, description, content_markdown, target_winrate, is_active, created_at, updated_at) VALUES (:id, :uid, 'PB', '', '', 0.5, true, :ts, :ts)"), {"id": playbook_id, "uid": user_id, "ts": datetime.now(timezone.utc)})
        await conn.execute(sa.text("INSERT INTO playbook_attachments (id, playbook_id, user_id, filename, content_type, storage_url, created_at) VALUES (:id, :pid, :uid, 'f.png', 'image/png', :url, :ts)"), {
                "id": attachment_id, "pid": playbook_id, "uid": user_id, "url": f"{public_url}/bucket/playbooks/img3.png", "ts": datetime.now(timezone.utc)
            })
    
    # 3. Upgrade to e6c9b3f1a2d0
    await asyncio.to_thread(run_alembic, "upgrade", "e6c9b3f1a2d0")
    
    # 4. Assert URLs were shortened to keys
    async with engine.connect() as conn:
        res = await conn.execute(sa.text("SELECT screenshot_urls FROM daily_checkins WHERE id = :id"), {"id": checkin_id})
        checkin_urls = res.scalar()
        assert checkin_urls == ["bucket/checkins/img1.png", "https://other.com/img.png", ""]
        
        res = await conn.execute(sa.text("SELECT image_urls FROM trades WHERE id = :id"), {"id": trade_id})
        trade_urls = res.scalar()
        assert trade_urls == ["bucket/trades/img2.png"]
        
        res = await conn.execute(sa.text("SELECT storage_url FROM playbook_attachments WHERE id = :id"), {"id": attachment_id})
        storage_url = res.scalar()
        assert storage_url == "bucket/playbooks/img3.png"
        
    # 5. Downgrade back to 314159265358 and assert URLs are reconstructed
    await asyncio.to_thread(run_alembic, "downgrade", "314159265358")
    
    async with engine.connect() as conn:
        res = await conn.execute(sa.text("SELECT screenshot_urls FROM daily_checkins WHERE id = :id"), {"id": checkin_id})
        checkin_urls = res.scalar()
        assert checkin_urls == [f"{public_url}/bucket/checkins/img1.png", "https://other.com/img.png", ""]
        
        res = await conn.execute(sa.text("SELECT image_urls FROM trades WHERE id = :id"), {"id": trade_id})
        trade_urls = res.scalar()
        assert trade_urls == [f"{public_url}/bucket/trades/img2.png"]
        
        res = await conn.execute(sa.text("SELECT storage_url FROM playbook_attachments WHERE id = :id"), {"id": attachment_id})
        storage_url = res.scalar()
        assert storage_url == f"{public_url}/bucket/playbooks/img3.png"
        
    # 6. Cleanup: bring DB back to head so other tests can run if needed.
    await asyncio.to_thread(run_alembic, "upgrade", "head")
    async with engine.begin() as conn:
        await conn.execute(sa.text("DELETE FROM users WHERE id = :id"), {"id": user_id})
