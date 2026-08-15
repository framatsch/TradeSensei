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

"""Unit tests for broker file parsers and ImportService.

All tests are pure unit tests — no database access (mocked).
"""

import uuid
from contextlib import ExitStack
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AccountNotFoundError, ImportParseError
from app.models.trade import AssetClass, Direction
from app.schemas.corporate_action import CorporateActionCreateRequest
from app.schemas.imports import ImportResult
from app.schemas.trade import TradeCreate
from app.services.import_service import ImportService
from app.utils.parsers.aggregator import TradeCreateWithSources
from app.utils.parsers.factory import BrokerType, get_parser
from app.utils.parsers.ibkr_xml import IBKRXMLParser

TEST_PORTFOLIO_ID = uuid.uuid4()

# ─── Helpers ──────────────────────────────────────────────────────────────────




# ─── Factory unit tests ───────────────────────────────────────────────────────


class TestGetParser:
    """Unit tests for the parser factory."""

    @pytest.mark.unit
    def test_returns_ibkr_xml_parser(self) -> None:
        """get_parser(IBKR) should return an IBKRXMLParser instance."""
        parser = get_parser(BrokerType.IBKR)
        assert isinstance(parser, IBKRXMLParser)

    @pytest.mark.unit
    def test_returns_schwab_parser(self) -> None:
        """get_parser(SCHWAB) should return the Schwab JSON parser."""
        parser = get_parser(BrokerType.SCHWAB)
        assert type(parser).__name__ == "SchwabJSONParser"


# ─── ImportService unit tests ─────────────────────────────────────────────────


def _make_trade_create(**kwargs: object) -> TradeCreate:
    """Build a minimal :class:`TradeCreate` payload.

    Args:
        **kwargs: Field overrides.

    Returns:
        A fully-validated :class:`TradeCreate` instance.
    """
    now = datetime.now(tz=UTC)
    defaults: dict[str, object] = {
        "symbol": "AAPL",
        "direction": Direction.LONG,
        "asset_class": AssetClass.EQUITY,
        "quantity": Decimal("10"),
        "entry_price": Decimal("150.00"),
        "opened_at": now,
    }
    defaults.update(kwargs)
    return TradeCreate(**defaults)  # type: ignore[arg-type]


@pytest.fixture()
def mock_session() -> AsyncMock:
    """Return a mock :class:`AsyncSession`."""
    session = AsyncMock()
    session.add = MagicMock()
    session.delete = MagicMock()
    return session


@pytest.fixture()
def import_service(mock_session: AsyncMock) -> ImportService:
    """Return an :class:`ImportService` wired to a mock session."""
    return ImportService(mock_session)


class TestImportService:
    """Unit tests for :class:`ImportService.import_file`."""

    @pytest.mark.unit
    async def test_raises_account_not_found_when_account_missing(
        self,
        import_service: ImportService,
    ) -> None:
        """import_file should raise AccountNotFoundError when account is missing."""
        with (
            patch(
                "app.services.import_service.AccountRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
            pytest.raises(AccountNotFoundError),
        ):
            await import_service.import_file(
                content=b"",
                filename="test.csv",
                broker=BrokerType.IBKR,
                portfolio_id=TEST_PORTFOLIO_ID,
                account_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
            )

    @pytest.mark.unit
    async def test_returns_import_result_on_success(
        self,
        import_service: ImportService,
    ) -> None:
        """import_file should return an ImportResult with correct counts."""
        fake_account = MagicMock()
        parsed_trades = [_make_trade_create(symbol="AAPL")]

        mock_parser = MagicMock()
        mock_parser.parse.return_value = (parsed_trades, [])
        mock_parser.warnings = []
        mock_parser.enrich_pnl_eur = AsyncMock(return_value=None)

        with (
            patch(
                "app.services.import_service.AccountRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=fake_account,
            ),
            patch(
                "app.services.import_service.CorporateActionRepository.list_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_open_lots_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_orphaned_lots_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_open_combo_positions_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_manually_edited_keys",
                new_callable=AsyncMock,
                return_value=set(),
            ),
            patch(
                "app.services.import_service.get_parser",
                return_value=mock_parser,
            ),
            patch(
                "app.services.import_service.TradeRepository.create",
                new_callable=AsyncMock,
                return_value=MagicMock(),
            ),
            patch(
                "app.services.import_service.PortfolioRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            result = await import_service.import_file(
                content=b"csv content",
                filename="activity.csv",
                broker=BrokerType.IBKR,
                portfolio_id=TEST_PORTFOLIO_ID,
                account_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
            )

        assert isinstance(result, ImportResult)
        assert result.trades_parsed == 1
        assert result.trades_created == 1
        assert result.trades_skipped == 0
        assert result.broker == "ibkr"
        assert result.filename == "activity.csv"

    @pytest.mark.unit
    async def test_zero_insert_raw_pipeline_skips_rebuild_without_override(
        self,
        import_service: ImportService,
    ) -> None:
        fake_account = MagicMock()
        user_id = uuid.uuid4()
        account_id = uuid.uuid4()

        raw_record = MagicMock()
        raw_record.id = "ibkr:raw-1"
        raw_record.model_copy = MagicMock(return_value=raw_record)

        mock_parser = MagicMock()
        mock_parser.parse_raw.return_value = ([raw_record], [])
        mock_parser.warnings = []
        mock_parser.enrich_pnl_eur = AsyncMock(return_value=None)

        with (
            patch(
                "app.services.import_service.AccountRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=fake_account,
            ),
            patch(
                "app.services.import_service.CorporateActionRepository.list_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_open_lots_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_orphaned_lots_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_open_combo_positions_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_manually_edited_keys",
                new_callable=AsyncMock,
                return_value=set(),
            ),
            patch(
                "app.services.import_service.BrokerRawTransactionRepository.bulk_upsert",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.BrokerRawTransactionRepository.list_released_without_execution",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.LogicalExecutionService.bulk_create_from_raw",
                new_callable=AsyncMock,
                return_value=([], 0),
            ),
            patch(
                "app.services.import_service.ImportService._collect_trade_creates_from_logical_batches",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.ImportService._build_seed_combo_execution_trades",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.get_parser",
                return_value=mock_parser,
            ),
            patch(
                "app.services.import_service.ExecutionRepository.delete_split_children_for_account",
                new_callable=AsyncMock,
            ) as delete_split,
            patch(
                "app.services.import_service.ExecutionRepository.restore_split_parents_for_account",
                new_callable=AsyncMock,
            ) as restore_parents,
            patch(
                "app.services.import_service.TradeRepository.delete_by_user_account",
                new_callable=AsyncMock,
            ) as delete_trades,
            patch(
                "app.services.import_service.PortfolioRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            result = await import_service.import_file(
                content=b"raw",
                filename="activity.xml",
                broker=BrokerType.IBKR,
                portfolio_id=TEST_PORTFOLIO_ID,
                account_id=account_id,
                user_id=user_id,
                overwrite_manually_edited=False,
            )

        assert result.raw_transactions_created == 0
        delete_split.assert_not_awaited()
        restore_parents.assert_not_awaited()
        delete_trades.assert_not_awaited()

    @pytest.mark.unit
    async def test_zero_insert_raw_pipeline_runs_rebuild_with_override(
        self,
        import_service: ImportService,
    ) -> None:
        fake_account = MagicMock()
        user_id = uuid.uuid4()
        account_id = uuid.uuid4()

        raw_record = MagicMock()
        raw_record.id = "ibkr:raw-1"
        raw_record.model_copy = MagicMock(return_value=raw_record)

        mock_parser = MagicMock()
        mock_parser.parse_raw.return_value = ([raw_record], [])
        mock_parser.warnings = []
        mock_parser.enrich_pnl_eur = AsyncMock(return_value=None)

        with (
            patch(
                "app.services.import_service.AccountRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=fake_account,
            ),
            patch(
                "app.services.import_service.CorporateActionRepository.list_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_open_lots_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_orphaned_lots_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_open_combo_positions_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_by_user_account",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_manually_edited_keys",
                new_callable=AsyncMock,
                return_value=set(),
            ),
            patch(
                "app.services.import_service.BrokerRawTransactionRepository.bulk_upsert",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.BrokerRawTransactionRepository.list_released_without_execution",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.LogicalExecutionService.bulk_create_from_raw",
                new_callable=AsyncMock,
                return_value=([], 0),
            ),
            patch(
                "app.services.import_service.ImportService._collect_trade_creates_from_logical_batches",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.ImportService._build_seed_combo_execution_trades",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.ImportService._backfill_execution_trade_links",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.import_service.ImportService._assign_position_ids_from_sources",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.import_service.get_parser",
                return_value=mock_parser,
            ),
            patch(
                "app.services.import_service.ExecutionRepository.delete_split_children_for_account",
                new_callable=AsyncMock,
                return_value=0,
            ) as delete_split,
            patch(
                "app.services.import_service.ExecutionRepository.restore_split_parents_for_account",
                new_callable=AsyncMock,
                return_value=0,
            ) as restore_parents,
            patch(
                "app.services.import_service.TradeRepository.delete_by_user_account",
                new_callable=AsyncMock,
            ) as delete_trades,
            patch(
                "app.services.import_service.PortfolioRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            result = await import_service.import_file(
                content=b"raw",
                filename="activity.xml",
                broker=BrokerType.IBKR,
                portfolio_id=TEST_PORTFOLIO_ID,
                account_id=account_id,
                user_id=user_id,
                overwrite_manually_edited=True,
            )

        assert result.raw_transactions_created == 0
        delete_split.assert_awaited_once_with(
            user_id=user_id,
            account_id=account_id,
            override=True,
        )
        restore_parents.assert_not_awaited()
        delete_trades.assert_awaited_once()

    @pytest.mark.unit
    async def test_non_zero_insert_raw_pipeline_runs_rebuild_without_override(
        self,
        import_service: ImportService,
    ) -> None:
        fake_account = MagicMock()
        user_id = uuid.uuid4()
        account_id = uuid.uuid4()

        raw_record = MagicMock()
        raw_record.id = "ibkr:raw-1"
        raw_record.model_copy = MagicMock(return_value=raw_record)

        inserted_raw = MagicMock()
        inserted_raw.id = raw_record.id

        mock_parser = MagicMock()
        mock_parser.parse_raw.return_value = ([raw_record], [])
        mock_parser.warnings = []
        mock_parser.enrich_pnl_eur = AsyncMock(return_value=None)

        with (
            patch(
                "app.services.import_service.AccountRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=fake_account,
            ),
            patch(
                "app.services.import_service.CorporateActionRepository.list_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_open_lots_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_orphaned_lots_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_open_combo_positions_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_by_user_account",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_manually_edited_keys",
                new_callable=AsyncMock,
                return_value=set(),
            ),
            patch(
                "app.services.import_service.BrokerRawTransactionRepository.bulk_upsert",
                new_callable=AsyncMock,
                return_value=[raw_record.id],
            ),
            patch(
                "app.services.import_service.BrokerRawTransactionRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=inserted_raw,
            ),
            patch(
                "app.services.import_service.LogicalExecutionService.bulk_create_from_raw",
                new_callable=AsyncMock,
                return_value=([], 0),
            ),
            patch(
                "app.services.import_service.ImportService._collect_trade_creates_from_logical_batches",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.ImportService._build_seed_combo_execution_trades",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.ImportService._backfill_execution_trade_links",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.import_service.ImportService._assign_position_ids_from_sources",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.import_service.get_parser",
                return_value=mock_parser,
            ),
            patch(
                "app.services.import_service.ExecutionRepository.delete_split_children_for_account",
                new_callable=AsyncMock,
                return_value=0,
            ) as delete_split,
            patch(
                "app.services.import_service.ExecutionRepository.restore_split_parents_for_account",
                new_callable=AsyncMock,
                return_value=0,
            ) as restore_parents,
            patch(
                "app.services.import_service.TradeRepository.delete_by_user_account",
                new_callable=AsyncMock,
            ) as delete_trades,
            patch(
                "app.services.import_service.PortfolioRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            result = await import_service.import_file(
                content=b"raw",
                filename="activity.xml",
                broker=BrokerType.IBKR,
                portfolio_id=TEST_PORTFOLIO_ID,
                account_id=account_id,
                user_id=user_id,
                overwrite_manually_edited=False,
            )

        assert result.raw_transactions_created == 1
        delete_split.assert_awaited_once_with(
            user_id=user_id,
            account_id=account_id,
            override=False,
        )
        restore_parents.assert_not_awaited()
        delete_trades.assert_awaited_once()

    @pytest.mark.unit
    async def test_import_updates_existing_corporate_action_instead_of_creating_duplicate(
        self,
        import_service: ImportService,
    ) -> None:
        fake_account = MagicMock()
        user_id = uuid.uuid4()
        account_id = uuid.uuid4()

        raw_record = MagicMock()
        raw_record.id = "ibkr:raw-1"
        raw_record.model_copy = MagicMock(return_value=raw_record)

        ca = CorporateActionCreateRequest(
            symbol="OTLK",
            date=datetime(2024, 3, 13, tzinfo=UTC).date(),
            ratio=Decimal("0.05"),
            old_conid="357194941",
            new_conid="690184975",
        )

        existing_action = MagicMock()
        existing_action.id = uuid.uuid4()
        existing_action.symbol = "OTLK"
        existing_action.date = datetime(2024, 3, 13, tzinfo=UTC).date()
        existing_action.ratio = Decimal("0.1")
        existing_action.old_conid = "old"
        existing_action.new_conid = "new"

        mock_parser = MagicMock()
        mock_parser.parse_raw.return_value = ([raw_record], [ca])
        mock_parser.warnings = []
        mock_parser.enrich_pnl_eur = AsyncMock(return_value=None)

        with (
            patch(
                "app.services.import_service.AccountRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=fake_account,
            ),
            patch(
                "app.services.import_service.CorporateActionRepository.list_by_user",
                new_callable=AsyncMock,
                side_effect=[[], [existing_action]],
            ),
            patch(
                "app.services.import_service.CorporateActionRepository.find_by_user_symbol_date",
                new_callable=AsyncMock,
                return_value=existing_action,
            ),
            patch(
                "app.services.import_service.CorporateActionRepository.create",
                new_callable=AsyncMock,
            ) as create_action,
            patch(
                "app.services.import_service.TradeRepository.list_open_lots_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_orphaned_lots_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_open_combo_positions_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_manually_edited_keys",
                new_callable=AsyncMock,
                return_value=set(),
            ),
            patch(
                "app.services.import_service.BrokerRawTransactionRepository.bulk_upsert",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.BrokerRawTransactionRepository.list_released_without_execution",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.LogicalExecutionService.bulk_create_from_raw",
                new_callable=AsyncMock,
                return_value=([], 0),
            ),
            patch(
                "app.services.import_service.ImportService._collect_trade_creates_from_logical_batches",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.ImportService._build_seed_combo_execution_trades",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.get_parser",
                return_value=mock_parser,
            ),
            patch(
                "app.services.import_service.ExecutionRepository.delete_split_children_for_account",
                new_callable=AsyncMock,
            ),
            patch(
                "app.services.import_service.ExecutionRepository.restore_split_parents_for_account",
                new_callable=AsyncMock,
            ),
            patch(
                "app.services.import_service.TradeRepository.delete_by_user_account",
                new_callable=AsyncMock,
            ),
            patch(
                "app.services.import_service.PortfolioRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            await import_service.import_file(
                content=b"raw",
                filename="activity.xml",
                broker=BrokerType.IBKR,
                portfolio_id=TEST_PORTFOLIO_ID,
                account_id=account_id,
                user_id=user_id,
                overwrite_manually_edited=False,
            )

        create_action.assert_not_awaited()
        assert existing_action.ratio == Decimal("0.05")
        assert existing_action.old_conid == "357194941"
        assert existing_action.new_conid == "690184975"
        import_service._session.flush.assert_awaited()

    @pytest.mark.unit
    async def test_anchor_reconcile_and_protection_result_counters(
        self,
        import_service: ImportService,
    ) -> None:
        """Task 15.3/15.5: anchor-based reconcile works across opened_at shifts,
        and ImportResult protection counters/warnings are populated.

        Scenario:
        - Trade A resolves only via anchor (legacy key mismatch due opened_at shift)
          and is reconciled onto an existing protected trade.
        - Trade B is manually protected but resolves to no existing trade and is
          therefore skipped with a warning.
        """
        fake_account = MagicMock()
        user_id = uuid.uuid4()
        account_id = uuid.uuid4()
        now = datetime(2026, 1, 3, 10, 0, tzinfo=UTC)

        incoming_reconcile = _make_trade_create(
            symbol="ANCHOR",
            broker_conid="111111111",
            opened_at=now,
        )
        incoming_skipped = _make_trade_create(
            symbol="SKIPME",
            broker_conid="222222222",
            opened_at=now.replace(hour=11),
        )

        tws_reconcile = TradeCreateWithSources(
            trade_create=incoming_reconcile,
            source_executions=[],
        )
        tws_skipped = TradeCreateWithSources(
            trade_create=incoming_skipped,
            source_executions=[],
        )

        existing_trade = MagicMock()
        existing_trade.id = uuid.uuid4()
        existing_trade.broker_conid = incoming_reconcile.broker_conid
        # Deliberately shifted so `(broker_conid, opened_at)` does not match.
        pre_reconcile_opened_at = now.replace(day=1)
        existing_trade.opened_at = pre_reconcile_opened_at
        existing_trade.is_manually_edited = True

        raw_record = MagicMock()
        raw_record.id = "raw-1"
        stamped_raw = MagicMock()
        stamped_raw.id = f"{user_id}:{raw_record.id}"
        raw_record.model_copy.return_value = stamped_raw
        mock_parser = MagicMock()
        mock_parser.parse_raw.return_value = ([raw_record], [])
        mock_parser.warnings = []
        mock_parser.enrich_pnl_eur = AsyncMock(return_value=None)

        manually_edited = {(incoming_skipped.broker_conid, incoming_skipped.opened_at)}

        with ExitStack() as stack:
            common_async_patches = [
                (
                    "app.services.import_service.AccountRepository.get_by_id",
                    fake_account,
                ),
                (
                    "app.services.import_service.CorporateActionRepository.list_by_user",
                    [],
                ),
                (
                    "app.services.import_service.TradeRepository.list_open_lots_by_user",
                    [],
                ),
                (
                    "app.services.import_service.TradeRepository.list_orphaned_lots_by_user",
                    [],
                ),
                (
                    "app.services.import_service.TradeRepository.list_open_combo_positions_by_user",
                    [],
                ),
                (
                    "app.services.import_service.TradeRepository.list_by_user_account",
                    [existing_trade],
                ),
                (
                    "app.services.import_service.TradeRepository.list_manually_edited_keys",
                    manually_edited,
                ),
                (
                    "app.services.import_service.TradeRepository.list_existing_entry_keys",
                    set(),
                ),
                (
                    "app.services.import_service.TradeRepository.list_existing_close_keys",
                    set(),
                ),
                (
                    "app.services.import_service.BrokerRawTransactionRepository.bulk_upsert",
                    [stamped_raw.id],
                ),
                (
                    "app.services.import_service.BrokerRawTransactionRepository.get_by_id",
                    MagicMock(id=stamped_raw.id),
                ),
                (
                    "app.services.import_service.BrokerRawTransactionRepository.list_released_without_execution",
                    [],
                ),
                (
                    "app.services.import_service.LogicalExecutionService.bulk_create_from_raw",
                    ([], 0),
                ),
                (
                    "app.services.import_service.ImportService._collect_trade_creates_from_logical_batches",
                    [],
                ),
                (
                    "app.services.import_service.ImportService._build_seed_combo_execution_trades",
                    [],
                ),
                (
                    "app.services.import_service.ImportService._resolve_anchor_trade_ids",
                    {0: existing_trade.id},
                ),
                (
                    "app.services.import_service.ImportService._assign_position_ids_from_sources",
                    None,
                ),
                (
                    "app.services.import_service.ExecutionRepository.list_by_trade_id",
                    [],
                ),
                (
                    "app.services.import_service.ExecutionRepository.delete_split_children_for_account",
                    0,
                ),
                (
                    "app.services.import_service.ExecutionRepository.restore_split_parents_for_account",
                    0,
                ),
                (
                    "app.services.import_service.TradeRepository.delete_by_user_account",
                    0,
                ),
                (
                    "app.services.import_service.PortfolioRepository.get_by_id",
                    None,
                ),
            ]
            for target, return_value in common_async_patches:
                stack.enter_context(
                    patch(target, new_callable=AsyncMock, return_value=return_value)
                )

            stack.enter_context(
                patch(
                    "app.services.import_service.build_combo_positions",
                    return_value=MagicMock(
                        fifo_executions=[], combo_trades=[], warnings=[]
                    ),
                )
            )
            stack.enter_context(
                patch(
                    "app.services.import_service.aggregate_executions_fifo_with_sources",
                    return_value=[tws_reconcile, tws_skipped],
                )
            )
            backfill_links = stack.enter_context(
                patch(
                    "app.services.import_service.ImportService._backfill_execution_trade_links",
                    new_callable=AsyncMock,
                )
            )
            stack.enter_context(
                patch(
                    "app.services.import_service.get_parser",
                    return_value=mock_parser,
                )
            )

            result = await import_service.import_file(
                content=b"raw",
                filename="activity.xml",
                broker=BrokerType.IBKR,
                portfolio_id=TEST_PORTFOLIO_ID,
                account_id=account_id,
                user_id=user_id,
                overwrite_manually_edited=False,
            )

        # Precondition: legacy key would not match before reconcile; only anchor
        # resolution can pick this trade.
        assert pre_reconcile_opened_at != incoming_reconcile.opened_at
        assert backfill_links.await_args is not None
        linked_tws = backfill_links.await_args.args[0]
        assert linked_tws[0].created_trade is existing_trade

        assert result.trades_protected_reconciled == 1
        assert result.trades_protected_skipped == 1
        assert any("protected_reconciled" in warning for warning in result.warnings)
        assert any("protected_skipped" in warning for warning in result.warnings)

    @pytest.mark.unit
    async def test_unlinked_protected_execution_is_reported_and_counted(
        self,
        import_service: ImportService,
    ) -> None:
        fake_account = MagicMock()
        user_id = uuid.uuid4()
        account_id = uuid.uuid4()
        now = datetime(2026, 1, 3, 10, 0, tzinfo=UTC)

        incoming = _make_trade_create(
            symbol="PROTUL",
            broker_conid="555555",
            opened_at=now,
        )

        tws = TradeCreateWithSources(trade_create=incoming, source_executions=[])

        protected_trade = MagicMock()
        protected_trade.id = uuid.uuid4()
        protected_trade.broker_conid = incoming.broker_conid
        protected_trade.opened_at = incoming.opened_at
        protected_trade.is_manually_edited = True

        raw_record = MagicMock()
        raw_record.id = "raw-prot-ul-1"
        stamped_raw = MagicMock()
        stamped_raw.id = f"{user_id}:{raw_record.id}"
        raw_record.model_copy.return_value = stamped_raw

        unlinked_execution = MagicMock()
        unlinked_execution.symbol = "PROTUL"
        unlinked_execution.conid = "555555"
        unlinked_execution.executed_at = now.replace(hour=11)

        mock_parser = MagicMock()
        mock_parser.parse_raw.return_value = ([raw_record], [])
        mock_parser.warnings = []
        mock_parser.enrich_pnl_eur = AsyncMock(return_value=None)

        with ExitStack() as stack:
            common_async_patches = [
                ("app.services.import_service.AccountRepository.get_by_id", fake_account),
                ("app.services.import_service.CorporateActionRepository.list_by_user", []),
                ("app.services.import_service.TradeRepository.list_open_lots_by_user", []),
                ("app.services.import_service.TradeRepository.list_orphaned_lots_by_user", []),
                ("app.services.import_service.TradeRepository.list_open_combo_positions_by_user", []),
                ("app.services.import_service.TradeRepository.list_by_user_account", [protected_trade]),
                ("app.services.import_service.TradeRepository.list_manually_edited_keys", set()),
                ("app.services.import_service.TradeRepository.list_existing_entry_keys", set()),
                ("app.services.import_service.TradeRepository.list_existing_close_keys", set()),
                ("app.services.import_service.TradeRepository.list_protected_trade_ids_by_user_account", [protected_trade.id]),
                ("app.services.import_service.BrokerRawTransactionRepository.bulk_upsert", [stamped_raw.id]),
                ("app.services.import_service.BrokerRawTransactionRepository.get_by_id", MagicMock(id=stamped_raw.id)),
                ("app.services.import_service.BrokerRawTransactionRepository.list_released_without_execution", []),
                ("app.services.import_service.LogicalExecutionService.bulk_create_from_raw", ([], 0)),
                ("app.services.import_service.ImportService._collect_trade_creates_from_logical_batches", []),
                ("app.services.import_service.ImportService._build_seed_combo_execution_trades", []),
                ("app.services.import_service.ImportService._resolve_anchor_trade_ids", {0: protected_trade.id}),
                ("app.services.import_service.ImportService._assign_position_ids_from_sources", None),
                ("app.services.import_service.ExecutionRepository.list_by_trade_id", []),
                ("app.services.import_service.ExecutionRepository.delete_split_children_for_account", 0),
                ("app.services.import_service.ExecutionRepository.restore_split_parents_for_account", 0),
                ("app.services.import_service.TradeRepository.delete_by_user_account", 0),
                ("app.services.import_service.PortfolioRepository.get_by_id", None),
            ]
            for target, return_value in common_async_patches:
                stack.enter_context(
                    patch(target, new_callable=AsyncMock, return_value=return_value)
                )

            stack.enter_context(
                patch(
                    "app.services.import_service.build_combo_positions",
                    return_value=MagicMock(fifo_executions=[], combo_trades=[], warnings=[]),
                )
            )
            stack.enter_context(
                patch(
                    "app.services.import_service.aggregate_executions_fifo_with_sources",
                    return_value=[tws],
                )
            )
            stack.enter_context(
                patch(
                    "app.services.import_service.ImportService._backfill_execution_trade_links",
                    new_callable=AsyncMock,
                    return_value=None,
                )
            )
            stack.enter_context(
                patch(
                    "app.services.import_service.ExecutionRepository.list_active_execution_contract_refs_by_trade_ids",
                    new_callable=AsyncMock,
                    side_effect=[
                        [
                            MagicMock(
                                execution_id=uuid.uuid4(),
                                symbol="PROTUL",
                                conid="555555",
                                trade_id=protected_trade.id,
                            )
                        ],
                        [
                            MagicMock(
                                execution_id=uuid.uuid4(),
                                symbol="PROTUL",
                                conid="555555",
                                trade_id=protected_trade.id,
                            )
                        ],
                    ],
                )
            )
            stack.enter_context(
                patch(
                    "app.services.import_service.ExecutionRepository.list_unlinked_by_source_ids_for_contracts",
                    new_callable=AsyncMock,
                    return_value=[unlinked_execution],
                )
            )
            stack.enter_context(
                patch(
                    "app.services.import_service.ExecutionRepository.has_unlinked_for_trade_contracts",
                    new_callable=AsyncMock,
                    return_value=False,
                )
            )
            stack.enter_context(
                patch(
                    "app.services.import_service.TradeRepository.get_by_id",
                    new_callable=AsyncMock,
                    return_value=protected_trade,
                )
            )
            stack.enter_context(
                patch(
                    "app.services.import_service.get_parser",
                    return_value=mock_parser,
                )
            )

            result = await import_service.import_file(
                content=b"raw",
                filename="activity.xml",
                broker=BrokerType.IBKR,
                portfolio_id=TEST_PORTFOLIO_ID,
                account_id=account_id,
                user_id=user_id,
                overwrite_manually_edited=False,
            )

        assert result.unlinked_executions == 1
        assert any("protected_unlinked_execution" in warning for warning in result.warnings)

    @pytest.mark.unit
    async def test_failed_trade_create_counted_as_skipped(
        self,
        import_service: ImportService,
    ) -> None:
        """Trades that fail to persist should be counted as skipped with warnings."""
        fake_account = MagicMock()
        parsed_trades = [
            _make_trade_create(symbol="AAPL"),
            _make_trade_create(symbol="MSFT"),
        ]

        mock_parser = MagicMock()
        mock_parser.parse.return_value = (parsed_trades, [])
        mock_parser.warnings = []
        mock_parser.enrich_pnl_eur = AsyncMock(return_value=None)

        call_count = 0

        async def create_side_effect(self_arg: object, trade: TradeCreate) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("DB error")
            return MagicMock()

        with (
            patch(
                "app.services.import_service.AccountRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=fake_account,
            ),
            patch(
                "app.services.import_service.CorporateActionRepository.list_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_open_lots_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_orphaned_lots_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_manually_edited_keys",
                new_callable=AsyncMock,
                return_value=set(),
            ),
            patch(
                "app.services.import_service.get_parser",
                return_value=mock_parser,
            ),
            patch(
                "app.services.import_service.TradeRepository.create",
                new=create_side_effect,
            ),
            patch(
                "app.services.import_service.PortfolioRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            result = await import_service.import_file(
                content=b"csv content",
                filename="activity.csv",
                broker=BrokerType.IBKR,
                portfolio_id=TEST_PORTFOLIO_ID,
                account_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
            )

        assert result.trades_created == 1
        assert result.trades_skipped == 1
        assert len(result.warnings) == 1

    @pytest.mark.unit
    async def test_parser_warnings_included_in_result(
        self,
        import_service: ImportService,
    ) -> None:
        """Warnings from the parser should be included in the ImportResult."""
        fake_account = MagicMock()

        mock_parser = MagicMock()
        mock_parser.parse.return_value = ([], [])
        mock_parser.warnings = ["IBKR row 3: skipped — bad data"]
        mock_parser.enrich_pnl_eur = AsyncMock(return_value=None)

        with (
            patch(
                "app.services.import_service.AccountRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=fake_account,
            ),
            patch(
                "app.services.import_service.CorporateActionRepository.list_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_open_lots_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_orphaned_lots_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_manually_edited_keys",
                new_callable=AsyncMock,
                return_value=set(),
            ),
            patch(
                "app.services.import_service.get_parser",
                return_value=mock_parser,
            ),
            patch(
                "app.services.import_service.PortfolioRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            result = await import_service.import_file(
                content=b"csv content",
                filename="activity.csv",
                broker=BrokerType.IBKR,
                portfolio_id=TEST_PORTFOLIO_ID,
                account_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
            )

        assert result.warnings == ["IBKR row 3: skipped — bad data"]
        assert result.trades_parsed == 0
        assert result.trades_created == 0
        assert result.trades_skipped == 0

    @pytest.mark.unit
    async def test_account_id_stamped_on_trade(
        self,
        import_service: ImportService,
    ) -> None:
        """The account_id should be set on each trade before persisting."""
        fake_account = MagicMock()
        target_account_id = uuid.uuid4()
        parsed_trades = [_make_trade_create(symbol="AAPL")]

        mock_parser = MagicMock()
        mock_parser.parse.return_value = (parsed_trades, [])
        mock_parser.warnings = []
        mock_parser.enrich_pnl_eur = AsyncMock(return_value=None)

        created_trades: list[TradeCreate] = []

        async def capture_create(self_arg: object, trade: TradeCreate) -> MagicMock:
            created_trades.append(trade)
            return MagicMock()

        with (
            patch(
                "app.services.import_service.AccountRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=fake_account,
            ),
            patch(
                "app.services.import_service.CorporateActionRepository.list_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_open_lots_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_orphaned_lots_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_manually_edited_keys",
                new_callable=AsyncMock,
                return_value=set(),
            ),
            patch(
                "app.services.import_service.get_parser",
                return_value=mock_parser,
            ),
            patch(
                "app.services.import_service.TradeRepository.create",
                new=capture_create,
            ),
            patch(
                "app.services.import_service.PortfolioRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            await import_service.import_file(
                content=b"csv content",
                filename="activity.csv",
                broker=BrokerType.IBKR,
                portfolio_id=TEST_PORTFOLIO_ID,
                account_id=target_account_id,
                user_id=uuid.uuid4(),
            )

        assert len(created_trades) == 1
        assert created_trades[0].account_id == target_account_id


# ─── IBKRXMLParser helpers ────────────────────────────────────────────────────


def _make_ibkr_xml(trades_xml: str = "") -> bytes:
    """Build a minimal IBKR Flex Query XML document.

    Args:
        trades_xml: Inner XML string containing ``<Trade>`` elements.

    Returns:
        UTF-8 encoded XML bytes.
    """
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<FlexQueryResponse>"
        "<FlexStatements>"
        "<FlexStatement>"
        "<Trades>"
        f"{trades_xml}"
        "</Trades>"
        "</FlexStatement>"
        "</FlexStatements>"
        "</FlexQueryResponse>"
    )
    return xml.encode("utf-8")


class TestIBKRXMLParserCashTradeFiltering:
    """Unit tests for IBKRXMLParser CASH asset category filtering."""

    @pytest.mark.unit
    def test_cash_trade_filtered_out_as_trade(self) -> None:
        """A <Trade assetCategory='CASH'> must NOT appear in the trades list."""
        from app.utils.parsers.ibkr_xml import IBKRXMLParser

        # A currency-conversion trade (EUR.USD)
        trade_xml = (
            '<Trade assetCategory="CASH" symbol="EUR.USD" tradeDate="20240315" '
            'dateTime="20240315;093000" quantity="1000" tradePrice="1.08" '
            'commission="-2.00" currency="USD" fifoPnlRealized="0" />'
        )
        xml_bytes = _make_ibkr_xml(trades_xml=trade_xml)
        parser = IBKRXMLParser()
        trades, _ = parser.parse(xml_bytes, "flex.xml")

        assert len(trades) == 0, "CASH assetCategory must not produce a Trade record"

    @pytest.mark.unit
    def test_normal_trade_still_parsed_alongside_cash_trade(self) -> None:
        """Filtering CASH trades must not affect normal STK trades."""
        from app.utils.parsers.ibkr_xml import IBKRXMLParser

        normal_trade = (
            '<Trade assetCategory="STK" symbol="AAPL" tradeDate="20240315" '
            'dateTime="20240315;093000" quantity="10" tradePrice="150.00" '
            'commission="-1.50" currency="USD" fifoPnlRealized="0" />'
        )
        cash_trade = (
            '<Trade assetCategory="CASH" symbol="EUR.USD" tradeDate="20240315" '
            'dateTime="20240315;093000" quantity="1000" tradePrice="1.08" '
            'commission="-2.00" currency="USD" fifoPnlRealized="0" />'
        )
        xml_bytes = _make_ibkr_xml(trades_xml=normal_trade + cash_trade)
        parser = IBKRXMLParser()
        trades, _ = parser.parse(xml_bytes, "flex.xml")

        assert len(trades) == 1
        assert trades[0].symbol == "AAPL"


# ─── Corporate action stub ─────────────────────────────────────────────────────


from dataclasses import dataclass  # noqa: E402
from datetime import date  # noqa: E402


@dataclass
class _CaSplitStub:
    """Minimal stub that satisfies the :class:`CorporateActionLike` protocol.

    Used in unit tests so that we do not need a real DB-backed
    :class:`~app.models.corporate_action.CorporateAction` instance.

    Attributes:
        symbol: Ticker symbol the corporate action applies to.
        date: Calendar date on which the split took effect.
        ratio: Split ratio (after / before shares).
        old_conid: Broker contract ID before the split.
        new_conid: Broker contract ID after the split.
    """

    symbol: str
    date: date
    ratio: Decimal
    old_conid: str | None
    new_conid: str | None


# ─── TestImportWithSplit ───────────────────────────────────────────────────────


class TestImportWithSplit:
    """Unit tests for split-adjusted FIFO aggregation and ImportService skip logic."""

    # ── aggregate_executions_fifo: 1:20 reverse split scenario ────────────────

    @pytest.mark.unit
    def test_reverse_split_adjusts_open_lot_and_produces_one_completed_trade(
        self,
    ) -> None:
        """A 1:20 reverse split should adjust the open lot and close correctly.

        Scenario (OTLK):
        1. Buy 1 000 shares  →  open lot
        2. 1:20 reverse split (ratio = 0.05) on 2023-05-01
           → lot becomes 50 shares at 20× the original entry price
        3. Sell 50 shares (with realised pnl) → 1 completed round-trip trade
        """
        from app.utils.parsers.aggregator import aggregate_executions_fifo

        buy_time = datetime(2023, 4, 1, 9, 30, tzinfo=UTC)
        sell_time = datetime(2023, 6, 1, 9, 30, tzinfo=UTC)

        buy_exec = _make_trade_create(
            symbol="OTLK",
            direction=Direction.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.00"),
            opened_at=buy_time,
            broker_conid="357194941",
        )
        sell_exec = _make_trade_create(
            symbol="OTLK",
            direction=Direction.SHORT,
            quantity=Decimal("50"),
            entry_price=Decimal("20.00"),
            opened_at=sell_time,
            pnl=Decimal("500.00"),
            broker_conid="690184975",
        )

        split = _CaSplitStub(
            symbol="OTLK",
            date=date(2023, 5, 1),
            ratio=Decimal("0.05"),
            old_conid="357194941",
            new_conid="690184975",
        )

        result = aggregate_executions_fifo(
            [buy_exec, sell_exec],
            corporate_actions=[split],
        )

        # Exactly one completed trade (the reversed-split lot closed by the sell)
        completed = [t for t in result if t.closed_at is not None]
        assert len(completed) == 1, (
            f"Expected exactly 1 completed trade, got {len(completed)}: "
            f"{[str(t) for t in result]}"
        )
        trade = completed[0]
        # After 1:20 split the 1 000-share lot becomes 50 shares
        assert trade.quantity == Decimal("50")
        assert trade.symbol == "OTLK"

    @pytest.mark.unit
    def test_reverse_split_adjusts_entry_price_by_inverse_ratio(self) -> None:
        """After a 1:20 reverse split the entry price must be divided by the ratio.

        Original entry price: $1.00.
        Ratio = 0.05  → adjusted entry price = $1.00 / 0.05 = $20.00.
        """
        from app.utils.parsers.aggregator import aggregate_executions_fifo

        buy_time = datetime(2023, 4, 1, 9, 30, tzinfo=UTC)
        sell_time = datetime(2023, 6, 1, 9, 30, tzinfo=UTC)

        buy_exec = _make_trade_create(
            symbol="OTLK",
            direction=Direction.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.00"),
            opened_at=buy_time,
            broker_conid="357194941",
        )
        sell_exec = _make_trade_create(
            symbol="OTLK",
            direction=Direction.SHORT,
            quantity=Decimal("50"),
            entry_price=Decimal("20.00"),
            opened_at=sell_time,
            pnl=Decimal("0"),
            broker_conid="690184975",
        )

        split = _CaSplitStub(
            symbol="OTLK",
            date=date(2023, 5, 1),
            ratio=Decimal("0.05"),
            old_conid="357194941",
            new_conid="690184975",
        )

        result = aggregate_executions_fifo(
            [buy_exec, sell_exec],
            corporate_actions=[split],
        )

        completed = [t for t in result if t.closed_at is not None]
        assert len(completed) == 1
        # entry_price of the stored lot: $1.00 / 0.05 = $20.00
        assert completed[0].entry_price == pytest.approx(Decimal("20.00"))

    @pytest.mark.unit
    def test_without_corporate_action_split_leaves_residual_open_lot(self) -> None:
        """Without a corporate action, only 50 of the 1 000-share lot are closed.

        When a 50-share closing execution arrives against a 1 000-share open lot
        (and no split has been registered), the FIFO aggregator matches what it
        can (50 shares → 1 completed trade) and leaves the residual 950 shares as
        an open lot.  The split test above demonstrates that registering the
        corporate action is what makes the lot sizes align exactly.
        """
        from app.utils.parsers.aggregator import aggregate_executions_fifo

        buy_time = datetime(2023, 4, 1, 9, 30, tzinfo=UTC)
        sell_time = datetime(2023, 6, 1, 9, 30, tzinfo=UTC)

        buy_exec = _make_trade_create(
            symbol="OTLK",
            direction=Direction.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.00"),
            opened_at=buy_time,
        )
        # pnl is set → treated as a closing leg by the aggregator
        sell_exec = _make_trade_create(
            symbol="OTLK",
            direction=Direction.SHORT,
            quantity=Decimal("50"),
            entry_price=Decimal("20.00"),
            opened_at=sell_time,
            pnl=Decimal("500.00"),
        )

        result = aggregate_executions_fifo([buy_exec, sell_exec])

        completed = [t for t in result if t.closed_at is not None]
        open_lots = [t for t in result if t.closed_at is None]
        # 50 shares closed, 950 shares still open (sizes did not match)
        assert len(completed) == 1
        assert len(open_lots) == 1
        assert open_lots[0].quantity == Decimal("950")

    @pytest.mark.unit
    def test_split_does_not_scale_commission(self) -> None:
        """Commission stays unchanged when a split is applied in FIFO aggregation."""
        from app.utils.parsers.aggregator import aggregate_executions_fifo

        buy_exec = _make_trade_create(
            symbol="OTLK",
            direction=Direction.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.00"),
            opened_at=datetime(2023, 4, 1, 9, 30, tzinfo=UTC),
            commission=Decimal("3.00"),
            broker_conid="357194941",
        )
        sell_exec = _make_trade_create(
            symbol="OTLK",
            direction=Direction.SHORT,
            quantity=Decimal("50"),
            entry_price=Decimal("20.00"),
            opened_at=datetime(2023, 6, 1, 9, 30, tzinfo=UTC),
            pnl=Decimal("500.00"),
            commission=Decimal("2.00"),
            broker_conid="690184975",
        )
        split = _CaSplitStub(
            symbol="OTLK",
            date=date(2023, 5, 1),
            ratio=Decimal("0.05"),
            old_conid="357194941",
            new_conid="690184975",
        )

        result = aggregate_executions_fifo([buy_exec, sell_exec], corporate_actions=[split])
        completed = [t for t in result if t.closed_at is not None]

        assert len(completed) == 1
        assert completed[0].commission == Decimal("5.00")

    # ── ImportService: skip_manually_edited ───────────────────────────────────

    @pytest.mark.unit
    async def test_import_service_skips_manually_edited_trade(
        self,
        import_service: ImportService,
    ) -> None:
        """import_file must skip trades whose (broker_conid, opened_at) key is in
        the manually-edited set, and count them in trades_skipped (not created).

        Scenario:
        - Parser produces two trades.
        - One trade's key is in the manually-edited set.
        - Only the other trade should be persisted (trades_created = 1).
        - The skipped trade should NOT appear in trades_created or trades_skipped
          (error-skipped); the result's trades_skipped counter reflects the
          difference between parsed and created + manually-edited.
        """
        fake_account = MagicMock()
        now = datetime.now(tz=UTC)

        # Two trades; the second will be in the manually-edited set.
        trade_a = _make_trade_create(
            symbol="AAPL",
            opened_at=now,
            broker_conid="111111111",
        )
        trade_b = _make_trade_create(
            symbol="OTLK",
            opened_at=now,
            broker_conid="357194941",
        )

        # The key for trade_b is in the manually-edited set.
        manually_edited: set[tuple[str | None, datetime]] = {
            ("357194941", now),
        }

        mock_parser = MagicMock()
        mock_parser.parse.return_value = ([trade_a, trade_b], [])
        mock_parser.warnings = []
        mock_parser.enrich_pnl_eur = AsyncMock(return_value=None)

        with (
            patch(
                "app.services.import_service.AccountRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=fake_account,
            ),
            patch(
                "app.services.import_service.CorporateActionRepository.list_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_open_lots_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_orphaned_lots_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_manually_edited_keys",
                new_callable=AsyncMock,
                return_value=manually_edited,
            ),
            patch(
                "app.services.import_service.get_parser",
                return_value=mock_parser,
            ),
            patch(
                "app.services.import_service.TradeRepository.create",
                new_callable=AsyncMock,
                return_value=MagicMock(),
            ),
            patch(
                "app.services.import_service.PortfolioRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            result = await import_service.import_file(
                content=b"csv content",
                filename="activity.csv",
                broker=BrokerType.IBKR,
                portfolio_id=TEST_PORTFOLIO_ID,
                account_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
            )

        # trade_a is persisted; trade_b is silently skipped (manually edited)
        assert result.trades_parsed == 2
        assert result.trades_created == 1
        # trades_skipped = parsed - created - manually_edited_skipped = 2 - 1 - 1 = 0
        assert result.trades_skipped == 0

    @pytest.mark.unit
    async def test_import_service_creates_all_when_no_manually_edited(
        self,
        import_service: ImportService,
    ) -> None:
        """All parsed trades should be created when the manually-edited set is empty."""
        fake_account = MagicMock()
        parsed_trades = [
            _make_trade_create(symbol="AAPL", broker_conid="111111111"),
            _make_trade_create(symbol="MSFT", broker_conid="222222222"),
        ]

        mock_parser = MagicMock()
        mock_parser.parse.return_value = (parsed_trades, [])
        mock_parser.warnings = []
        mock_parser.enrich_pnl_eur = AsyncMock(return_value=None)

        with (
            patch(
                "app.services.import_service.AccountRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=fake_account,
            ),
            patch(
                "app.services.import_service.CorporateActionRepository.list_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_open_lots_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_orphaned_lots_by_user",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.import_service.TradeRepository.list_manually_edited_keys",
                new_callable=AsyncMock,
                return_value=set(),
            ),
            patch(
                "app.services.import_service.get_parser",
                return_value=mock_parser,
            ),
            patch(
                "app.services.import_service.TradeRepository.create",
                new_callable=AsyncMock,
                return_value=MagicMock(),
            ),
            patch(
                "app.services.import_service.PortfolioRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            result = await import_service.import_file(
                content=b"csv content",
                filename="activity.csv",
                broker=BrokerType.IBKR,
                portfolio_id=TEST_PORTFOLIO_ID,
                account_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
            )

        assert result.trades_parsed == 2
        assert result.trades_created == 2
        assert result.trades_skipped == 0


class TestIBKRXMLParserCommission:
    """Unit tests for IBKRXMLParser commission parsing."""

    @pytest.mark.unit
    def test_commission_max_of_ib_and_gen(self) -> None:
        """When both commission fields are present, max absolute value is used."""
        from app.utils.parsers.ibkr_xml import IBKRXMLParser

        trade_xml = (
            '<Trade assetCategory="STK" symbol="AAPL" tradeDate="20240315" '
            'dateTime="20240315;093000" quantity="10" tradePrice="150.00" '
            'ibCommission="-1.00" commission="-1.50" currency="USD" '
            'fifoPnlRealized="0" />'
        )
        xml_bytes = _make_ibkr_xml(trades_xml=trade_xml)
        parser = IBKRXMLParser()
        trades, _ = parser.parse(xml_bytes, "flex.xml")

        assert len(trades) == 1
        assert trades[0].commission == Decimal("1.50")

    @pytest.mark.unit
    def test_commission_zero_ib_and_nonzero_gen(self) -> None:
        """When ibCommission is 0, the non-zero commission value is used."""
        from app.utils.parsers.ibkr_xml import IBKRXMLParser

        trade_xml = (
            '<Trade assetCategory="STK" symbol="AAPL" tradeDate="20240315" '
            'dateTime="20240315;093000" quantity="10" tradePrice="150.00" '
            'ibCommission="0" commission="-2.50" currency="USD" '
            'fifoPnlRealized="0" />'
        )
        xml_bytes = _make_ibkr_xml(trades_xml=trade_xml)
        parser = IBKRXMLParser()
        trades, _ = parser.parse(xml_bytes, "flex.xml")

        assert len(trades) == 1
        assert trades[0].commission == Decimal("2.50")
