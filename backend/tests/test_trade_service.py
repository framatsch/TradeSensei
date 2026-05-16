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

"""Unit tests for TradeService — no database access (all DB calls mocked)."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import InvalidCursorError, TradeNotFoundError
from app.models.trade import AssetClass, Direction, Trade
from app.schemas.trade import TradeCreate, TradePartialCloseRequest, TradeRead, TradeUpdate
from app.services.trade_service import TradeService


def _make_trade(
    id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    account_id: uuid.UUID | None = None,
    position_id: uuid.UUID | None = None,
    playbook_id: uuid.UUID | None = None,
    symbol: str = "AAPL",
    direction: Direction = Direction.LONG,
    asset_class: AssetClass = AssetClass.EQUITY,
    quantity: Decimal = Decimal("10"),
    entry_price: Decimal = Decimal("150.00"),
    exit_price: Decimal | None = None,
    stop_loss: Decimal | None = None,
    take_profit: Decimal | None = None,
    opened_at: datetime | None = None,
    closed_at: datetime | None = None,
    pnl: Decimal | None = None,
    commission: Decimal = Decimal("0"),
    multiplier: int = 1,
    currency: str | None = None,
    notes: str | None = None,
    user_rating: int | None = None,
    image_urls: list[str] | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> Trade:
    """Build a minimal :class:`Trade` ORM instance for testing.

    Uses explicit typed parameters instead of ``**kwargs`` to satisfy
    mypy strict mode without suppression comments.

    Args:
        id: UUID primary key. Defaults to a new random UUID.
        user_id: User ID. Defaults to a new random UUID.
        account_id: Account ID. Defaults to None.
        symbol: Ticker symbol. Defaults to ``"AAPL"``.
        direction: Trade direction. Defaults to ``Direction.LONG``.
        asset_class: Asset class. Defaults to ``AssetClass.EQUITY``.
        quantity: Position size. Defaults to ``Decimal("10")``.
        entry_price: Entry price. Defaults to ``Decimal("150.00")``.
        exit_price: Exit price. Defaults to ``None``.
        stop_loss: Stop-loss price. Defaults to ``None``.
        take_profit: Take-profit price. Defaults to ``None``.
        opened_at: Open timestamp. Defaults to now (UTC).
        closed_at: Close timestamp. Defaults to ``None``.
        pnl: Realised PnL. Defaults to ``None``.
        commission: Commission paid. Defaults to ``Decimal("0")``.
        notes: Free-text notes. Defaults to ``None``.
        created_at: Row-creation timestamp. Defaults to now (UTC).
        updated_at: Row-update timestamp. Defaults to now (UTC).

    Returns:
        A :class:`Trade` with sensible defaults.
    """
    now = datetime.now(tz=UTC)
    trade = Trade()
    # Assigning to Mapped[] descriptor attributes directly is required for
    # constructing detached ORM instances in tests; mypy treats these as
    # SQLCoreOperations at the class level but they behave as plain values
    # on instances.  The assignments are correct at runtime.
    trade.id = id if id is not None else uuid.uuid4()  # type: ignore[assignment]
    trade.user_id = user_id if user_id is not None else uuid.uuid4()  # type: ignore[assignment]
    trade.account_id = account_id  # type: ignore[assignment]
    trade.position_id = (
        position_id if position_id is not None else uuid.uuid4()
    )  # type: ignore[assignment]
    trade.playbook_id = playbook_id  # type: ignore[assignment]
    trade.symbol = symbol  # type: ignore[assignment]
    trade.direction = direction  # type: ignore[assignment]
    trade.asset_class = asset_class  # type: ignore[assignment]
    trade.quantity = quantity  # type: ignore[assignment]
    trade.entry_price = entry_price  # type: ignore[assignment]
    trade.exit_price = exit_price  # type: ignore[assignment]
    trade.stop_loss = stop_loss  # type: ignore[assignment]
    trade.take_profit = take_profit  # type: ignore[assignment]
    trade.opened_at = opened_at if opened_at is not None else now  # type: ignore[assignment]
    trade.closed_at = closed_at  # type: ignore[assignment]
    trade.pnl = pnl  # type: ignore[assignment]
    trade.commission = commission  # type: ignore[assignment]
    trade.multiplier = multiplier  # type: ignore[assignment]
    trade.currency = currency  # type: ignore[assignment]
    trade.notes = notes  # type: ignore[assignment]
    trade.user_rating = user_rating  # type: ignore[assignment]
    trade.created_at = created_at if created_at is not None else now  # type: ignore[assignment]
    trade.updated_at = updated_at if updated_at is not None else now  # type: ignore[assignment]
    trade.image_urls = []  # type: ignore[assignment]
    trade.is_manually_edited = False  # type: ignore[assignment]
    trade.is_modelbook = False  # type: ignore[assignment]
    trade.is_combo = False  # type: ignore[assignment]
    trade.tags = []  # type: ignore[assignment]
    trade.trade_notes = []  # type: ignore[assignment]
    return trade


def _make_create_payload(**kwargs: object) -> TradeCreate:
    """Build a minimal valid :class:`TradeCreate` payload.

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
def service(mock_session: AsyncMock) -> TradeService:
    """Return a :class:`TradeService` wired to a mock session."""
    return TradeService(mock_session)


class TestCreateTrade:
    """Unit tests for :meth:`TradeService.create_trade`."""

    @pytest.mark.unit
    async def test_returns_trade_read(
        self, service: TradeService, mock_session: AsyncMock
    ) -> None:
        """create_trade should return a TradeRead DTO."""
        trade = _make_trade()
        with (
            patch(
                "app.services.trade_service.TradeRepository.create",
                new_callable=AsyncMock,
                return_value=trade,
            ),
            patch(
                "app.services.trade_service.AccountRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.repositories.execution.ExecutionRepository.create",
                new_callable=AsyncMock,
            ) as mock_exec_create,
            patch(
                "app.services.trade_service.TradeService._re_aggregate_trade",
                new_callable=AsyncMock,
            ) as mock_reaggregate,
            patch(
                "app.services.trade_service.TradeRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=trade,
            ),
        ):
            result = await service.create_trade(_make_create_payload())

        assert isinstance(result, TradeRead)
        assert result.symbol == "AAPL"
        mock_exec_create.assert_awaited_once()
        mock_reaggregate.assert_awaited_once_with(trade.id)

    @pytest.mark.unit
    async def test_create_trade_auto_creates_execution(
        self, service: TradeService, mock_session: AsyncMock
    ) -> None:
        """create_trade should automatically create a LogicalExecution."""
        from app.models.logical_execution import EXECUTION_ORIGIN_MANUAL

        trade = _make_trade(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            account_id=uuid.uuid4(),
            symbol="MSFT",
            direction=Direction.SHORT,
            quantity=Decimal("50"),
            entry_price=Decimal("300.00"),
            commission=Decimal("1.50"),
            opened_at=datetime.now(tz=UTC),
            multiplier=1,
            currency="USD",
        )

        with (
            patch(
                "app.services.trade_service.TradeRepository.create",
                new_callable=AsyncMock,
                return_value=trade,
            ),
            patch(
                "app.services.trade_service.AccountRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.repositories.execution.ExecutionRepository.create",
                new_callable=AsyncMock,
            ) as mock_exec_create,
            patch(
                "app.services.trade_service.TradeService._re_aggregate_trade",
                new_callable=AsyncMock,
            ),
            patch(
                "app.services.trade_service.TradeRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=trade,
            ),
        ):
            await service.create_trade(_make_create_payload())

        mock_exec_create.assert_awaited_once_with(
            user_id=trade.user_id,
            account_id=trade.account_id,
            symbol=trade.symbol,
            asset_class=trade.asset_class,
            direction=trade.direction,
            quantity=trade.quantity,
            price=trade.entry_price,
            commission=trade.commission,
            executed_at=trade.opened_at,
            multiplier=trade.multiplier,
            currency=trade.currency,
            origin=EXECUTION_ORIGIN_MANUAL,
            trade_id=trade.id,
        )

    @pytest.mark.unit

    @pytest.mark.unit
    async def test_create_trade_with_manual_executions(
        self, service: TradeService, mock_session: AsyncMock
    ) -> None:
        import uuid
        from datetime import UTC, datetime
        from decimal import Decimal

        from app.models.logical_execution import EXECUTION_ORIGIN_MANUAL
        from app.models.trade import AssetClass, Direction
        from app.schemas.execution import LogicalExecutionCreate
        from app.schemas.trade import TradeCreate

        trade_id = uuid.uuid4()
        user_id = uuid.uuid4()
        opened_at = datetime.now(UTC)

        trade = _make_trade(
            id=trade_id, user_id=user_id, symbol="MANUAL_EXEC", direction=Direction.LONG
        )
        
        leg = LogicalExecutionCreate(
            direction=Direction.LONG,
            quantity=Decimal("10"),
            price=Decimal("100"),
            commission=Decimal("1"),
            executed_at=opened_at,
            pnl=None,
        )

        data = TradeCreate(
            user_id=user_id,
            symbol="MANUAL_EXEC",
            direction=Direction.LONG,
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("10"),
            entry_price=Decimal("100"),
            opened_at=opened_at,
            commission=Decimal("1"),
            executions=[leg],
        )

        with (
            patch(
                "app.services.trade_service.TradeRepository.create",
                new_callable=AsyncMock,
                return_value=trade,
            ),
            patch(
                "app.services.trade_service.TradeRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=trade,
            ),
            patch(
                "app.services.trade_service.AccountRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.repositories.execution.ExecutionRepository.create",
                new_callable=AsyncMock,
            ) as mock_exec_create,
            patch(
                "app.services.trade_service.TradeService._re_aggregate_trade",
                new_callable=AsyncMock,
            ) as mock_re_aggregate,
        ):
            created = await service.create_trade(data)
            
            assert created.symbol == "MANUAL_EXEC"
            mock_exec_create.assert_called_once_with(
                user_id=user_id,
                account_id=trade.account_id,
                symbol="MANUAL_EXEC",
                asset_class=AssetClass.EQUITY,
                direction=Direction.LONG,
                quantity=Decimal("10"),
                price=Decimal("100"),
                commission=Decimal("1"),
                executed_at=opened_at,
                multiplier=trade.multiplier,
                currency=trade.currency,
                origin=EXECUTION_ORIGIN_MANUAL,
                trade_id=trade_id,
                pnl=None,
            )
            mock_re_aggregate.assert_called_once_with(trade_id)

    async def test_create_closed_trade_creates_entry_and_exit_executions(
        self, service: TradeService, mock_session: AsyncMock
    ) -> None:
        """create_trade with exit_price+closed_at creates entry and exit executions."""
        from app.models.logical_execution import EXECUTION_ORIGIN_MANUAL

        now = datetime.now(tz=UTC)
        closed = datetime.now(tz=UTC)
        trade = _make_trade(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            account_id=None,
            symbol="AAPL",
            direction=Direction.LONG,
            quantity=Decimal("10"),
            entry_price=Decimal("150.00"),
            exit_price=Decimal("160.00"),
            opened_at=now,
            closed_at=closed,
            pnl=Decimal("100.00"),
        )

        payload = TradeCreate(
            user_id=trade.user_id,
            symbol="AAPL",
            direction=Direction.LONG,
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("10"),
            entry_price=Decimal("150.00"),
            exit_price=Decimal("160.00"),
            opened_at=now,
            closed_at=closed,
            pnl=Decimal("100.00"),
        )

        with (
            patch(
                "app.services.trade_service.TradeRepository.create",
                new_callable=AsyncMock,
                return_value=trade,
            ),
            patch(
                "app.services.trade_service.AccountRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.repositories.execution.ExecutionRepository.create",
                new_callable=AsyncMock,
            ) as mock_exec_create,
            patch(
                "app.services.trade_service.TradeService._re_aggregate_trade",
                new_callable=AsyncMock,
            ) as mock_reaggregate,
            patch(
                "app.services.trade_service.TradeRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=trade,
            ),
        ):
            await service.create_trade(payload)

        # Two executions must be created: entry (LONG) and exit (SHORT).
        assert mock_exec_create.await_count == 2
        calls = mock_exec_create.call_args_list
        entry_kwargs = calls[0].kwargs
        exit_kwargs = calls[1].kwargs
        assert entry_kwargs["direction"] == Direction.LONG
        assert entry_kwargs["price"] == Decimal("150.00")
        assert entry_kwargs["origin"] == EXECUTION_ORIGIN_MANUAL
        assert exit_kwargs["direction"] == Direction.SHORT
        assert exit_kwargs["price"] == Decimal("160.00")
        assert exit_kwargs["pnl"] == Decimal("100.00")
        assert exit_kwargs["origin"] == EXECUTION_ORIGIN_MANUAL
        # Re-aggregation must NOT run for an already-closed trade.
        mock_reaggregate.assert_not_awaited()


class TestGetTrade:
    """Unit tests for :meth:`TradeService.get_trade`."""

    @pytest.mark.unit
    async def test_returns_trade_read_when_found(self, service: TradeService) -> None:
        """get_trade should return a TradeRead when the trade exists."""
        trade = _make_trade()
        with patch(
            "app.services.trade_service.TradeRepository.get_by_id",
            new_callable=AsyncMock,
            return_value=trade,
        ):
            result = await service.get_trade(  # type: ignore[arg-type]
                trade.id,
                trade.user_id,
            )

        assert isinstance(result, TradeRead)
        assert result.id == trade.id  # type: ignore[comparison-overlap]

    @pytest.mark.unit
    async def test_raises_not_found_when_missing(self, service: TradeService) -> None:
        """get_trade should raise TradeNotFoundError when the trade is missing."""
        with (
            patch(
                "app.services.trade_service.TradeRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
            pytest.raises(TradeNotFoundError),
        ):
            await service.get_trade(uuid.uuid4(), uuid.uuid4())


class TestListTrades:
    """Unit tests for :meth:`TradeService.list_trades`."""

    @pytest.mark.unit
    async def test_returns_cursor_page(self, service: TradeService) -> None:
        """list_trades should return a CursorPage with the mapped DTOs."""
        trades = [_make_trade(symbol=f"T{i}") for i in range(3)]
        with patch(
            "app.services.trade_service.TradeRepository.list_cursor",
            new_callable=AsyncMock,
            return_value=(trades, None, 3),
        ):
            page = await service.list_trades(limit=20, cursor=None, include_total=True)

        assert page.total == 3
        assert len(page.items) == 3
        assert page.next_cursor is None

    @pytest.mark.unit
    async def test_forwards_account_ids_to_repository(self, service: TradeService) -> None:
        """list_trades should pass selected account IDs through to the repository."""
        account_ids = [uuid.uuid4(), uuid.uuid4()]
        with patch(
            "app.services.trade_service.TradeRepository.list_cursor",
            new_callable=AsyncMock,
            return_value=([], None, None),
        ) as list_cursor:
            await service.list_trades(limit=20, cursor=None, account_ids=account_ids)

        assert list_cursor.await_args is not None
        assert list_cursor.await_args.kwargs["account_ids"] == account_ids

    @pytest.mark.unit
    async def test_raises_invalid_cursor_on_bad_cursor(
        self, service: TradeService
    ) -> None:
        """list_trades should raise InvalidCursorError for an invalid cursor."""
        with (
            patch(
                "app.services.trade_service.TradeRepository.list_cursor",
                new_callable=AsyncMock,
                side_effect=ValueError("Invalid pagination cursor"),
            ),
            pytest.raises(InvalidCursorError),
        ):
            await service.list_trades(limit=20, cursor="bad!!!")


class TestUpdateTrade:
    """Unit tests for :meth:`TradeService.update_trade`."""

    @pytest.mark.unit
    async def test_returns_updated_trade_read(self, service: TradeService) -> None:
        """update_trade should return the updated TradeRead DTO."""
        trade = _make_trade()
        updated = _make_trade(symbol="TSLA")
        with (
            patch(
                "app.services.trade_service.TradeRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=trade,
            ),
            patch(
                "app.services.trade_service.TradeRepository.update",
                new_callable=AsyncMock,
                return_value=updated,
            ),
        ):
            result = await service.update_trade(
                trade.id,  # type: ignore[arg-type]
                TradeUpdate(symbol="TSLA"),
                trade.user_id,
            )

        assert result.symbol == "TSLA"

    @pytest.mark.unit
    async def test_raises_not_found_when_missing(self, service: TradeService) -> None:
        """update_trade should raise TradeNotFoundError when trade is missing."""
        with (
            patch(
                "app.services.trade_service.TradeRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
            pytest.raises(TradeNotFoundError),
        ):
            await service.update_trade(
                uuid.uuid4(),
                TradeUpdate(symbol="X"),
                uuid.uuid4(),
            )

    @pytest.mark.unit
    async def test_propagates_metadata_to_open_position_siblings(
        self, service: TradeService
    ) -> None:
        """update_trade should propagate metadata fields to open siblings."""
        position_id = uuid.uuid4()
        trade = _make_trade(position_id=position_id)
        updated = _make_trade(position_id=position_id)
        user_id = trade.user_id
        assert user_id is not None

        with (
            patch(
                "app.services.trade_service.TradeRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=trade,
            ),
            patch(
                "app.services.trade_service.TradeRepository.update",
                new_callable=AsyncMock,
                return_value=updated,
            ),
            patch(
                "app.services.trade_service.TradeRepository.propagate_metadata_to_open_position_group",
                new_callable=AsyncMock,
                return_value=2,
            ) as mock_propagate,
        ):
            result = await service.update_trade(
                trade.id,  # type: ignore[arg-type]
                TradeUpdate(notes="updated", user_rating=4),
                user_id,
            )

        assert isinstance(result, TradeRead)
        mock_propagate.assert_awaited_once_with(
            source_trade=updated,
            data=TradeUpdate(notes="updated", user_rating=4),
            user_id=user_id,
            compare_updated_at=trade.updated_at,
        )


class TestTradeUpdateNullableSentinel:
    """Tests verifying the nullable sentinel behaviour of :class:`TradeUpdate`.

    Pydantic v2 distinguishes between a field that was **omitted** from the
    request payload (not in ``model_fields_set``) and one that was
    **explicitly set to null** (present in ``model_fields_set`` with value
    ``None``).  The repository uses ``model_dump(exclude_unset=True)`` so
    that only the latter actually clears the DB column.
    """

    @pytest.mark.unit
    def test_explicit_null_stop_loss_is_in_fields_set(self) -> None:
        """TradeUpdate with stop_loss=None should include it in model_fields_set."""
        payload = TradeUpdate(stop_loss=None)
        assert "stop_loss" in payload.model_fields_set
        assert payload.stop_loss is None

    @pytest.mark.unit
    def test_omitted_stop_loss_not_in_fields_set(self) -> None:
        """TradeUpdate without stop_loss should NOT include it in model_fields_set."""
        payload = TradeUpdate(symbol="AAPL")
        assert "stop_loss" not in payload.model_fields_set

    @pytest.mark.unit
    def test_explicit_null_take_profit_is_in_fields_set(self) -> None:
        """TradeUpdate with take_profit=None should include it in model_fields_set."""
        payload = TradeUpdate(take_profit=None)
        assert "take_profit" in payload.model_fields_set
        assert payload.take_profit is None

    @pytest.mark.unit
    def test_omitted_take_profit_not_in_fields_set(self) -> None:
        """TradeUpdate without take_profit should NOT include it in model_fields_set."""
        payload = TradeUpdate(symbol="AAPL")
        assert "take_profit" not in payload.model_fields_set

    @pytest.mark.unit
    def test_model_dump_exclude_unset_includes_explicit_null(self) -> None:
        """model_dump(exclude_unset=True) should include fields set to null."""
        payload = TradeUpdate(stop_loss=None, symbol="TSLA")
        dumped = payload.model_dump(exclude_unset=True)
        assert "stop_loss" in dumped
        assert dumped["stop_loss"] is None
        assert dumped["symbol"] == "TSLA"

    @pytest.mark.unit
    def test_model_dump_exclude_unset_excludes_omitted_fields(self) -> None:
        """model_dump(exclude_unset=True) should exclude fields that were omitted."""
        payload = TradeUpdate(symbol="TSLA")
        dumped = payload.model_dump(exclude_unset=True)
        assert "stop_loss" not in dumped
        assert "take_profit" not in dumped
        assert dumped["symbol"] == "TSLA"

    @pytest.mark.unit
    async def test_update_trade_passes_null_stop_loss_to_repo(
        self, service: TradeService
    ) -> None:
        """update_trade should call repo.update with the full TradeUpdate payload.

        The repository is responsible for applying model_dump(exclude_unset=True),
        so we verify the service passes the unmodified payload through.
        """
        trade = _make_trade(stop_loss=Decimal("148.00"))
        updated = _make_trade(stop_loss=None)
        clear_payload = TradeUpdate(stop_loss=None)

        with (
            patch(
                "app.services.trade_service.TradeRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=trade,
            ),
            patch(
                "app.services.trade_service.TradeRepository.update",
                new_callable=AsyncMock,
                return_value=updated,
            ) as mock_update,
        ):
            result = await service.update_trade(
                trade.id,  # type: ignore[arg-type]
                clear_payload,
                trade.user_id,
            )

        # Verify the repo received the exact payload (not a mutated copy)
        mock_update.assert_awaited_once_with(trade, clear_payload)
        assert result.stop_loss is None


class TestDeleteTrade:
    """Unit tests for :meth:`TradeService.delete_trade`."""

    @pytest.mark.unit
    async def test_delete_calls_repo(self, service: TradeService) -> None:
        """delete_trade should call the repository delete method."""
        trade = _make_trade()
        mock_delete = AsyncMock()
        with (
            patch(
                "app.services.trade_service.TradeRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=trade,
            ),
            patch(
                "app.services.trade_service.TradeRepository.delete",
                new=mock_delete,
            ),
            patch(
                "app.services.trade_service.ExecutionRepository.list_by_trade_id",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            await service.delete_trade(trade.id, trade.user_id)  # type: ignore[arg-type]

        mock_delete.assert_awaited_once_with(trade)

    @pytest.mark.unit
    async def test_raises_not_found_when_missing(self, service: TradeService) -> None:
        """delete_trade should raise TradeNotFoundError when trade is missing."""
        with (
            patch(
                "app.services.trade_service.TradeRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
            pytest.raises(TradeNotFoundError),
        ):
            await service.delete_trade(uuid.uuid4(), uuid.uuid4())


class TestPortfolioCacheInvalidation:
    """Unit tests for cache invalidation hooks in trade service methods."""

    @pytest.mark.unit
    async def test_bulk_assign_playbook_invalidates_portfolio_cache(
        self, service: TradeService
    ) -> None:
        user_id = uuid.uuid4()
        portfolio_id = uuid.uuid4()

        with (
            patch(
                "app.services.trade_service.PlaybookRepository.get_by_id",
                new_callable=AsyncMock,
                return_value=type("_Playbook", (), {"user_id": user_id})(),
            ),
            patch(
                "app.services.trade_service.TradeRepository.bulk_assign_playbook",
                new_callable=AsyncMock,
                return_value=1,
            ),
            patch.object(
                service._cache,
                "invalidate_portfolio",
                new_callable=AsyncMock,
            ) as invalidate,
        ):
            count = await service.bulk_assign_playbook(
                trade_ids=[uuid.uuid4()],
                playbook_id=uuid.uuid4(),
                user_id=user_id,
                portfolio_id=portfolio_id,
            )

        assert count == 1
        invalidate.assert_awaited_once_with(portfolio_id, user_id)

    @pytest.mark.unit
    async def test_merge_trades_invalidates_portfolio_cache(
        self, service: TradeService
    ) -> None:
        user_id = uuid.uuid4()
        portfolio_id = uuid.uuid4()
        account_id = uuid.uuid4()
        t1 = _make_trade(
            id=uuid.uuid4(),
            user_id=user_id,
            account_id=account_id,
            symbol="AAPL",
            opened_at=datetime(2025, 1, 1, tzinfo=UTC),
        )
        t2 = _make_trade(
            id=uuid.uuid4(),
            user_id=user_id,
            account_id=account_id,
            symbol="AAPL",
            opened_at=datetime(2025, 1, 2, tzinfo=UTC),
        )

        with (
            patch.object(
                service._repo,
                "get_by_id",
                new_callable=AsyncMock,
                side_effect=[t1, t2, t1],
            ),
            patch.object(service._repo, "delete", new_callable=AsyncMock),
            patch.object(
                service._cache,
                "invalidate_portfolio",
                new_callable=AsyncMock,
            ) as invalidate,
            patch(
                "app.repositories.execution.ExecutionRepository",
                return_value=type(
                    "_ExecRepo",
                    (),
                    {
                        "list_by_trade_id": AsyncMock(return_value=[]),
                        "reassign_to_trade": AsyncMock(return_value=0),
                    },
                )(),
            ),
            patch.object(service, "_re_aggregate_trade", new_callable=AsyncMock),
        ):
            _ = await service.merge_trades(
                trade_ids=[t1.id, t2.id],
                user_id=user_id,
                portfolio_id=portfolio_id,
            )

        invalidate.assert_awaited_once_with(portfolio_id, user_id)

    @pytest.mark.unit
    async def test_partial_close_trade_invalidates_cache_via_account_lookup(
        self, service: TradeService
    ) -> None:
        user_id = uuid.uuid4()
        portfolio_id = uuid.uuid4()
        account_id = uuid.uuid4()
        trade = _make_trade(
            id=uuid.uuid4(),
            user_id=user_id,
            account_id=account_id,
            symbol="AAPL",
            quantity=Decimal("5"),
            entry_price=Decimal("100"),
            opened_at=datetime(2025, 1, 1, tzinfo=UTC),
        )
        request = TradePartialCloseRequest(
            quantity=Decimal("5"),
            exit_price=Decimal("110"),
            closed_at=datetime(2025, 1, 2, tzinfo=UTC),
            exit_commission=Decimal("0"),
        )

        with (
            patch.object(
                service._repo,
                "get_by_id",
                new_callable=AsyncMock,
                return_value=trade,
            ),
            patch.object(
                service._account_repo,
                "get_by_id",
                new_callable=AsyncMock,
                return_value=type("_Account", (), {"portfolio_id": portfolio_id})(),
            ),
            patch.object(service, "_re_aggregate_trade", new_callable=AsyncMock),
            patch.object(service._session, "add"),
            patch.object(service._session, "flush", new_callable=AsyncMock),
            patch.object(service._session, "commit", new_callable=AsyncMock),
            patch.object(
                service._cache,
                "invalidate_portfolio",
                new_callable=AsyncMock,
            ) as invalidate,
        ):
            await service.partial_close_trade(
                trade_id=trade.id,
                request=request,
                user_id=user_id,
                portfolio_id=portfolio_id,
            )

        invalidate.assert_awaited_once_with(portfolio_id, user_id)
