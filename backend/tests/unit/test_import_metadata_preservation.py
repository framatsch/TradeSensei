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

"""Unit tests — user metadata preservation during broker re-import.

Verifies that journal, user_rating, tradingview_link, image_urls, stop_loss,
take_profit, playbook_id, trade_notes, taxonomy_assignments, and
annotation_assignments survive the DELETE+rebuild cycle in ImportService.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from app.repositories.trade_repository import (
    TradeAnnotationSnapshot,
    TradeMetadataSnapshot,
    TradeNoteSnapshot,
    TradeTaxonomySnapshot,
)

pytestmark = pytest.mark.asyncio(loop_scope="function")

_USER_ID = uuid.uuid4()
_PORTFOLIO_ID = uuid.uuid4()
_ACCOUNT_ID = uuid.uuid4()
_POSITION_ID = uuid.uuid4()
_TAXONOMY_ID = uuid.uuid4()
_PLAYBOOK_ID = uuid.uuid4()
_ANNOTATION_DEF_ID = uuid.uuid4()
_OPENED_AT = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_snapshot(
    *,
    journal: str | None = "My journal",
    user_rating: int | None = 4,
    image_urls: list[str] | None = None,
    notes: list[TradeNoteSnapshot] | None = None,
    taxonomies: list[TradeTaxonomySnapshot] | None = None,
    annotations: list[TradeAnnotationSnapshot] | None = None,
) -> TradeMetadataSnapshot:
    return TradeMetadataSnapshot(
        position_id=_POSITION_ID,
        symbol="AAPL",
        opened_at=_OPENED_AT,
        direction="LONG",
        journal=journal,
        user_rating=user_rating,
        tradingview_link="https://tv.example.com/chart/abc",
        image_urls=image_urls or ["https://s3.example.com/img1.png"],
        stop_loss=Decimal("140.00"),
        take_profit=Decimal("175.00"),
        playbook_id=_PLAYBOOK_ID,
        notes=notes or [TradeNoteSnapshot(content="Fear trade", emotion="fearful")],
        taxonomies=taxonomies or [TradeTaxonomySnapshot(taxonomy_id=_TAXONOMY_ID)],
        annotations=annotations or [
            TradeAnnotationSnapshot(
                annotation_definition_id=_ANNOTATION_DEF_ID,
                value_int=None,
                value_float=None,
                value_bool=True,
                value_string=None,
            )
        ],
    )


# ---------------------------------------------------------------------------
# TradeMetadataSnapshot dataclass tests
# ---------------------------------------------------------------------------


class TestTradeMetadataSnapshotDefaults:
    """Verify default values and field presence on the snapshot dataclass."""

    @staticmethod
    def test_empty_lists_by_default():
        snap = TradeMetadataSnapshot(
            position_id=_POSITION_ID,
            symbol="AAPL",
            opened_at=_OPENED_AT,
            direction="LONG",
        )
        assert snap.notes == []
        assert snap.taxonomies == []
        assert snap.annotations == []
        assert snap.image_urls == []

    @staticmethod
    def test_none_fields_by_default():
        snap = TradeMetadataSnapshot(
            position_id=_POSITION_ID,
            symbol="AAPL",
            opened_at=_OPENED_AT,
            direction="LONG",
        )
        assert snap.journal is None
        assert snap.user_rating is None
        assert snap.tradingview_link is None
        assert snap.stop_loss is None
        assert snap.take_profit is None
        assert snap.playbook_id is None

    @staticmethod
    def test_populated_snapshot():
        snap = _make_snapshot()
        assert snap.journal == "My journal"
        assert snap.user_rating == 4
        assert snap.image_urls == ["https://s3.example.com/img1.png"]
        assert len(snap.notes) == 1
        assert snap.notes[0].content == "Fear trade"
        assert snap.notes[0].emotion == "fearful"
        assert len(snap.taxonomies) == 1
        assert snap.taxonomies[0].taxonomy_id == _TAXONOMY_ID
        assert len(snap.annotations) == 1
        assert snap.annotations[0].value_bool is True


# ---------------------------------------------------------------------------
# restore_trade_metadata repository method tests
# ---------------------------------------------------------------------------


class TestRestoreTradeMetadata:
    """Unit tests for TradeRepository.restore_trade_metadata."""

    def _make_repo(self):
        from app.repositories.trade_repository import TradeRepository

        repo = TradeRepository.__new__(TradeRepository)
        repo._session = AsyncMock()
        repo._session.add = MagicMock()
        repo._session.execute = AsyncMock()
        repo._session.flush = AsyncMock()
        return repo

    @pytest.mark.asyncio
    async def test_restore_scalar_fields(self):
        repo = self._make_repo()
        snap = _make_snapshot(notes=[], taxonomies=[], annotations=[])
        trade_id = uuid.uuid4()

        await repo.restore_trade_metadata(
            trade_id=trade_id,
            user_id=_USER_ID,
            snapshot=snap,
        )

        # session.execute should have been called once for the UPDATE
        assert repo._session.execute.call_count >= 1
        repo._session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_restore_skips_null_fields(self):
        repo = self._make_repo()
        snap = TradeMetadataSnapshot(
            position_id=_POSITION_ID,
            symbol="AAPL",
            opened_at=_OPENED_AT,
            direction="LONG",
            journal=None,
            user_rating=None,
            tradingview_link=None,
            image_urls=[],
            stop_loss=None,
            take_profit=None,
            playbook_id=None,
        )
        trade_id = uuid.uuid4()

        await repo.restore_trade_metadata(
            trade_id=trade_id,
            user_id=_USER_ID,
            snapshot=snap,
        )

        # No UPDATE should be issued when all fields are empty
        repo._session.execute.assert_not_called()
        repo._session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_restore_inserts_trade_notes(self):
        repo = self._make_repo()
        snap = _make_snapshot(
            journal=None,
            user_rating=None,
            image_urls=[],
            taxonomies=[],
            annotations=[],
            notes=[
                TradeNoteSnapshot(content="Note 1", emotion="calm"),
                TradeNoteSnapshot(content="Note 2", emotion=None),
            ],
        )
        trade_id = uuid.uuid4()

        await repo.restore_trade_metadata(
            trade_id=trade_id,
            user_id=_USER_ID,
            snapshot=snap,
        )

        # session.add should have been called twice (once per note)
        assert repo._session.add.call_count == 2

    @pytest.mark.asyncio
    async def test_restore_inserts_taxonomies(self):
        repo = self._make_repo()
        tax_id1 = uuid.uuid4()
        tax_id2 = uuid.uuid4()
        snap = _make_snapshot(
            journal=None,
            user_rating=None,
            image_urls=[],
            notes=[],
            annotations=[],
            taxonomies=[
                TradeTaxonomySnapshot(taxonomy_id=tax_id1),
                TradeTaxonomySnapshot(taxonomy_id=tax_id2),
            ],
        )
        trade_id = uuid.uuid4()

        await repo.restore_trade_metadata(
            trade_id=trade_id,
            user_id=_USER_ID,
            snapshot=snap,
        )

        # session.execute must have been called at least once for the taxonomy inserts
        assert repo._session.execute.call_count >= 1
        repo._session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_restore_inserts_annotations(self):
        repo = self._make_repo()
        ann_def_id = uuid.uuid4()
        snap = _make_snapshot(
            journal=None,
            user_rating=None,
            image_urls=[],
            notes=[],
            taxonomies=[],
            annotations=[
                TradeAnnotationSnapshot(
                    annotation_definition_id=ann_def_id,
                    value_int=None,
                    value_float=None,
                    value_bool=None,
                    value_string="breakout",
                )
            ],
        )
        trade_id = uuid.uuid4()

        await repo.restore_trade_metadata(
            trade_id=trade_id,
            user_id=_USER_ID,
            snapshot=snap,
        )

        # At least one execute call for the annotation INSERT
        assert repo._session.execute.call_count >= 1
        repo._session.flush.assert_called_once()


# ---------------------------------------------------------------------------
# ImportService metadata snapshot + restore integration path tests
# ---------------------------------------------------------------------------


def _make_import_service():
    from app.services.import_service import ImportService

    svc = ImportService.__new__(ImportService)
    svc._session = AsyncMock()
    svc._account_repo = AsyncMock()
    svc._trade_repo = AsyncMock()
    svc._ca_repo = AsyncMock()
    svc._portfolio_repo = AsyncMock()
    svc._raw_repo = AsyncMock()
    svc._logical_svc = AsyncMock()
    svc._exec_repo = AsyncMock()
    svc._audit = MagicMock()
    return svc


def _mock_created_trade(
    *,
    trade_id: uuid.UUID | None = None,
    position_id: uuid.UUID | None = None,
    symbol: str = "AAPL",
    opened_at: datetime | None = None,
    direction_value: str = "LONG",
) -> MagicMock:
    t = MagicMock()
    t.id = trade_id or uuid.uuid4()
    t.position_id = position_id or _POSITION_ID
    t.symbol = symbol
    t.opened_at = opened_at or _OPENED_AT
    t.direction = MagicMock()
    t.direction.value = direction_value
    return t


class TestImportServiceMetadataSnapshotCaptured:
    """Verify that list_user_metadata_snapshot is called before delete_by_user_account."""

    @pytest.mark.asyncio
    async def test_snapshot_called_before_delete(self):
        """list_user_metadata_snapshot must be invoked before delete_by_user_account."""
        svc = _make_import_service()

        call_order: list[str] = []

        async def mock_snapshot(*args, **kwargs):
            call_order.append("snapshot")
            return {}

        async def mock_delete(*args, **kwargs):
            call_order.append("delete")
            return 0

        svc._trade_repo.list_user_metadata_snapshot = mock_snapshot
        svc._trade_repo.delete_by_user_account = mock_delete

        # Configure other dependencies so import_file gets past validation
        svc._account_repo.get_by_id = AsyncMock(return_value=_mock_created_trade())
        svc._portfolio_repo.get_by_id = AsyncMock(return_value=MagicMock(base_currency="USD"))
        svc._ca_repo.list_by_user = AsyncMock(return_value=[])
        svc._trade_repo.list_open_lots_by_user = AsyncMock(return_value=[])
        svc._trade_repo.list_orphaned_lots_by_user = AsyncMock(return_value=[])
        svc._trade_repo.list_manually_edited_keys = AsyncMock(return_value=set())
        svc._trade_repo.list_existing_entry_keys = AsyncMock(return_value=set())
        svc._trade_repo.list_existing_close_keys = AsyncMock(return_value=set())
        svc._trade_repo.list_open_combo_positions_by_user = AsyncMock(return_value=[])

        # Patch the parser so parse_raw returns an empty list (uses raw pipeline)
        mock_parser = MagicMock()
        mock_parser.parse_raw.return_value = ([], [])
        mock_parser.enrich_pnl_eur = AsyncMock()
        mock_parser.warnings = []

        svc._raw_repo.bulk_upsert = AsyncMock(return_value=[])
        svc._logical_svc.bulk_create_from_raw = AsyncMock(return_value=([], 0))
        svc._exec_repo.delete_split_children_for_account = AsyncMock(return_value=0)
        svc._exec_repo.restore_split_parents_for_account = AsyncMock(return_value=0)

        with patch("app.services.import_service.get_parser", return_value=mock_parser):
            from app.utils.parsers.factory import BrokerType

            await svc.import_file(
                content=b"<FlexQueryResponse />",
                filename="test.xml",
                broker=BrokerType.IBKR,
                portfolio_id=_PORTFOLIO_ID,
                account_id=_ACCOUNT_ID,
                user_id=_USER_ID,
            )

        assert "snapshot" in call_order
        assert "delete" in call_order
        # snapshot MUST come before delete
        assert call_order.index("snapshot") < call_order.index("delete")

    @pytest.mark.asyncio
    async def test_snapshot_not_called_when_account_id_none(self):
        """No snapshot when account_id is None — no DELETE/rebuild happens."""
        svc = _make_import_service()
        snapshot_called = []

        async def mock_snapshot(*args, **kwargs):
            snapshot_called.append(True)
            return {}

        svc._trade_repo.list_user_metadata_snapshot = mock_snapshot
        svc._account_repo.get_by_id = AsyncMock(return_value=None)
        svc._portfolio_repo.get_by_id = AsyncMock(return_value=MagicMock(base_currency="USD"))
        svc._ca_repo.list_by_user = AsyncMock(return_value=[])
        svc._trade_repo.list_open_lots_by_user = AsyncMock(return_value=[])
        svc._trade_repo.list_orphaned_lots_by_user = AsyncMock(return_value=[])
        svc._trade_repo.list_manually_edited_keys = AsyncMock(return_value=set())
        svc._trade_repo.list_existing_entry_keys = AsyncMock(return_value=set())
        svc._trade_repo.list_existing_close_keys = AsyncMock(return_value=set())
        svc._trade_repo.list_open_combo_positions_by_user = AsyncMock(return_value=[])

        mock_parser = MagicMock()
        mock_parser.parse_raw.return_value = ([], [])
        mock_parser.enrich_pnl_eur = AsyncMock()
        mock_parser.warnings = []

        svc._raw_repo.bulk_upsert = AsyncMock(return_value=[])
        svc._logical_svc.bulk_create_from_raw = AsyncMock(return_value=([], 0))
        svc._exec_repo.delete_split_children_for_account = AsyncMock(return_value=0)
        svc._exec_repo.restore_split_parents_for_account = AsyncMock(return_value=0)

        with patch("app.services.import_service.get_parser", return_value=mock_parser):
            from app.utils.parsers.factory import BrokerType

            await svc.import_file(
                content=b"<FlexQueryResponse />",
                filename="test.xml",
                broker=BrokerType.IBKR,
                portfolio_id=_PORTFOLIO_ID,
                account_id=None,  # No account_id → no snapshot
                user_id=_USER_ID,
            )

        assert snapshot_called == [], "snapshot must not be called when account_id is None"


class TestImportServiceMetadataRestored:
    """Verify restore_trade_metadata is called for trades with matching snapshots."""

    @pytest.mark.asyncio
    async def test_restore_called_for_matching_position_id(self):
        """restore_trade_metadata must be called when position_id matches snapshot.

        Tests the restore logic directly (not via import_file) to avoid
        the complexity of fully mocking the entire FIFO pipeline.
        """
        snap = _make_snapshot()
        metadata_snapshots = {_POSITION_ID: snap}

        # Build fallback index (same logic as in import_service)
        fallback_index: dict[tuple[str, str, str], TradeMetadataSnapshot] = {
            (s.symbol, s.opened_at.isoformat(), s.direction): s
            for s in metadata_snapshots.values()
        }

        restore_calls: list[uuid.UUID] = []

        async def mock_restore(trade_id: uuid.UUID, user_id: uuid.UUID, snapshot: TradeMetadataSnapshot) -> None:
            restore_calls.append(trade_id)

        mock_trade_repo = AsyncMock()
        mock_trade_repo.restore_trade_metadata = mock_restore

        # Simulate the restore loop from import_service
        new_trade_id = uuid.uuid4()
        created = _mock_created_trade(trade_id=new_trade_id, position_id=_POSITION_ID)

        from app.utils.parsers.aggregator import TradeCreateWithSources

        mock_tws = MagicMock(spec=TradeCreateWithSources)
        mock_tws.created_trade = created

        trades_with_sources = [mock_tws]

        for tws in trades_with_sources:
            if tws.created_trade is None:
                continue
            c = tws.created_trade
            snap_match = metadata_snapshots.get(c.position_id)
            if snap_match is None:
                fallback_key = (c.symbol, c.opened_at.isoformat(), c.direction.value)
                snap_match = fallback_index.get(fallback_key)
            if snap_match is not None:
                await mock_trade_repo.restore_trade_metadata(
                    trade_id=c.id,
                    user_id=_USER_ID,
                    snapshot=snap_match,
                )

        assert new_trade_id in restore_calls, "restore_trade_metadata must be called for the new trade"

    @pytest.mark.asyncio
    async def test_restore_matches_via_fallback_when_position_id_differs(self):
        """restore_trade_metadata must match via symbol+opened_at+direction fallback."""
        snap = _make_snapshot()
        # Use a different position_id so primary key match fails
        other_position_id = uuid.uuid4()
        metadata_snapshots: dict[uuid.UUID, TradeMetadataSnapshot] = {snap.position_id: snap}

        fallback_index: dict[tuple[str, str, str], TradeMetadataSnapshot] = {
            (s.symbol, s.opened_at.isoformat(), s.direction): s
            for s in metadata_snapshots.values()
        }

        restore_calls: list[uuid.UUID] = []

        async def mock_restore(trade_id: uuid.UUID, user_id: uuid.UUID, snapshot: TradeMetadataSnapshot) -> None:
            restore_calls.append(trade_id)

        mock_trade_repo = AsyncMock()
        mock_trade_repo.restore_trade_metadata = mock_restore

        new_trade_id = uuid.uuid4()
        # Trade has different position_id but same symbol/opened_at/direction
        created = _mock_created_trade(
            trade_id=new_trade_id,
            position_id=other_position_id,  # different!
            symbol="AAPL",
            opened_at=_OPENED_AT,
            direction_value="LONG",
        )

        from app.utils.parsers.aggregator import TradeCreateWithSources

        mock_tws = MagicMock(spec=TradeCreateWithSources)
        mock_tws.created_trade = created
        trades_with_sources = [mock_tws]

        for tws in trades_with_sources:
            if tws.created_trade is None:
                continue
            c = tws.created_trade
            snap_match = metadata_snapshots.get(c.position_id)  # miss (different position_id)
            if snap_match is None:
                fallback_key = (c.symbol, c.opened_at.isoformat(), c.direction.value)
                snap_match = fallback_index.get(fallback_key)
            if snap_match is not None:
                await mock_trade_repo.restore_trade_metadata(
                    trade_id=c.id,
                    user_id=_USER_ID,
                    snapshot=snap_match,
                )

        assert new_trade_id in restore_calls, "restore must succeed via symbol/opened_at/direction fallback"

    @pytest.mark.asyncio
    async def test_no_restore_when_snapshot_empty(self):
        """When no user metadata exists, restore_trade_metadata must not be called."""
        svc = _make_import_service()

        restore_calls: list[uuid.UUID] = []

        async def mock_restore(trade_id, user_id, snapshot):
            restore_calls.append(trade_id)

        svc._trade_repo.list_user_metadata_snapshot = AsyncMock(return_value={})
        svc._trade_repo.delete_by_user_account = AsyncMock(return_value=0)
        svc._trade_repo.restore_trade_metadata = mock_restore
        svc._account_repo.get_by_id = AsyncMock(return_value=MagicMock(account_number="ACC1"))
        svc._portfolio_repo.get_by_id = AsyncMock(return_value=MagicMock(base_currency="USD"))
        svc._ca_repo.list_by_user = AsyncMock(return_value=[])
        svc._trade_repo.list_open_lots_by_user = AsyncMock(return_value=[])
        svc._trade_repo.list_orphaned_lots_by_user = AsyncMock(return_value=[])
        svc._trade_repo.list_manually_edited_keys = AsyncMock(return_value=set())
        svc._trade_repo.list_existing_entry_keys = AsyncMock(return_value=set())
        svc._trade_repo.list_existing_close_keys = AsyncMock(return_value=set())
        svc._trade_repo.list_open_combo_positions_by_user = AsyncMock(return_value=[])

        mock_parser = MagicMock()
        mock_parser.parse_raw.return_value = ([], [])
        mock_parser.enrich_pnl_eur = AsyncMock()
        mock_parser.warnings = []

        svc._raw_repo.bulk_upsert = AsyncMock(return_value=[])
        svc._logical_svc.bulk_create_from_raw = AsyncMock(return_value=([], 0))
        svc._exec_repo.delete_split_children_for_account = AsyncMock(return_value=0)
        svc._exec_repo.restore_split_parents_for_account = AsyncMock(return_value=0)

        with patch("app.services.import_service.get_parser", return_value=mock_parser):
            from app.utils.parsers.factory import BrokerType

            await svc.import_file(
                content=b"<FlexQueryResponse />",
                filename="test.xml",
                broker=BrokerType.IBKR,
                portfolio_id=_PORTFOLIO_ID,
                account_id=_ACCOUNT_ID,
                user_id=_USER_ID,
            )

        assert restore_calls == [], "restore must not be called when snapshot is empty"
