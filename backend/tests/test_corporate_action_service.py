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

"""Unit tests for CorporateActionService — no database access (all DB calls mocked).

All patches target the repository class methods that the service delegates to.
The mock session is provided by the shared ``mock_session`` fixture from
``conftest.py``.
"""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import CorporateActionConflictError, CorporateActionNotFoundError
from app.models.corporate_action import CorporateAction
from app.schemas.corporate_action import (
    CorporateActionCreate,
    CorporateActionRead,
    CorporateActionUpdate,
)
from app.services.corporate_action_service import CorporateActionService

# ── Patch base path ────────────────────────────────────────────────────────────

_REPO = "app.services.corporate_action_service.CorporateActionRepository"


# ── Helper ─────────────────────────────────────────────────────────────────────


def _make_ca(
    id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    symbol: str = "OTLK",
    action_date: date | None = None,
    ratio: Decimal | None = None,
    old_conid: str | None = "357194941",
    new_conid: str | None = "690184975",
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> CorporateAction:
    """Build a minimal :class:`CorporateAction` ORM instance for testing.

    Args:
        id: UUID primary key. Defaults to a new random UUID.
        user_id: UUID of the owning user. Defaults to a new random UUID.
        symbol: Ticker symbol. Defaults to ``"OTLK"``.
        action_date: Effective date of the corporate action.
            Defaults to ``2023-05-01``.
        ratio: Split ratio as a :class:`Decimal`.
            Defaults to ``Decimal("0.05")`` (1:20 reverse split).
        old_conid: Broker conid before the split.
            Defaults to ``"357194941"``.
        new_conid: Broker conid after the split.
            Defaults to ``"690184975"``.
        created_at: Row-creation timestamp. Defaults to now (UTC).
        updated_at: Row-update timestamp. Defaults to now (UTC).

    Returns:
        A :class:`CorporateAction` ORM instance with sensible defaults.
    """
    now = datetime.now(tz=UTC)
    ca = CorporateAction()
    ca.id = id if id is not None else uuid.uuid4()  # type: ignore[assignment]
    ca.user_id = user_id if user_id is not None else uuid.uuid4()  # type: ignore[assignment]
    ca.symbol = symbol  # type: ignore[assignment]
    ca.date = action_date if action_date is not None else date(2023, 5, 1)  # type: ignore[assignment]
    ca.ratio = ratio if ratio is not None else Decimal("0.05")  # type: ignore[assignment]
    ca.old_conid = old_conid  # type: ignore[assignment]
    ca.new_conid = new_conid  # type: ignore[assignment]
    ca.created_at = created_at if created_at is not None else now  # type: ignore[assignment]
    ca.updated_at = updated_at if updated_at is not None else now  # type: ignore[assignment]
    return ca


# ── Fixture ────────────────────────────────────────────────────────────────────


@pytest.fixture()
def service(mock_session: AsyncMock) -> CorporateActionService:
    """Return a :class:`CorporateActionService` wired to a mock session."""
    return CorporateActionService(mock_session)


# ── TestListCorporateActions ───────────────────────────────────────────────────


class TestListCorporateActions:
    """Unit tests for :meth:`CorporateActionService.list_corporate_actions`."""

    @pytest.mark.unit
    async def test_returns_list_of_corporate_action_reads(
        self, service: CorporateActionService
    ) -> None:
        """list_corporate_actions should return a list of CorporateActionRead DTOs."""
        actions = [_make_ca(symbol=f"SYM{i}") for i in range(3)]
        with patch(
            f"{_REPO}.list_by_user",
            new_callable=AsyncMock,
            return_value=actions,
        ):
            result = await service.list_corporate_actions(uuid.uuid4())

        assert len(result) == 3
        assert all(isinstance(r, CorporateActionRead) for r in result)
        symbols = {r.symbol for r in result}
        assert symbols == {"SYM0", "SYM1", "SYM2"}

    @pytest.mark.unit
    async def test_returns_empty_list_when_none(
        self, service: CorporateActionService
    ) -> None:
        """list_corporate_actions should return an empty list when there are
        no records."""
        with patch(
            f"{_REPO}.list_by_user",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await service.list_corporate_actions(uuid.uuid4())

        assert result == []


# ── TestGetCorporateAction ─────────────────────────────────────────────────────


class TestGetCorporateAction:
    """Unit tests for :meth:`CorporateActionService.get_corporate_action`."""

    @pytest.mark.unit
    async def test_returns_corporate_action_read_when_found(
        self, service: CorporateActionService
    ) -> None:
        """get_corporate_action should return a CorporateActionRead DTO
        when the record exists."""
        ca = _make_ca(symbol="OTLK", ratio=Decimal("0.05"))
        with patch(
            f"{_REPO}.get_by_id",
            new_callable=AsyncMock,
            return_value=ca,
        ):
            result = await service.get_corporate_action(
                ca.id,  # type: ignore[arg-type]
                ca.user_id,  # type: ignore[arg-type]
            )

        assert isinstance(result, CorporateActionRead)
        assert result.symbol == "OTLK"
        assert result.ratio == Decimal("0.05")

    @pytest.mark.unit
    async def test_raises_not_found_when_missing(
        self, service: CorporateActionService
    ) -> None:
        """get_corporate_action should raise CorporateActionNotFoundError
        when record is absent."""
        with (
            patch(
                f"{_REPO}.get_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
            pytest.raises(CorporateActionNotFoundError),
        ):
            await service.get_corporate_action(uuid.uuid4(), uuid.uuid4())


# ── TestCreateCorporateAction ──────────────────────────────────────────────────


class TestCreateCorporateAction:
    """Unit tests for :meth:`CorporateActionService.create_corporate_action`."""

    @pytest.mark.unit
    async def test_returns_corporate_action_read_with_correct_data(
        self, service: CorporateActionService
    ) -> None:
        """create_corporate_action should return a CorporateActionRead
        with matching fields."""
        user_id = uuid.uuid4()
        ca = _make_ca(
            user_id=user_id,
            symbol="OTLK",
            ratio=Decimal("0.05"),
            old_conid="357194941",
            new_conid="690184975",
        )
        with (
            patch(
                f"{_REPO}.find_by_user_symbol_date",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                f"{_REPO}.create",
                new_callable=AsyncMock,
                return_value=ca,
            ),
            patch.object(service, "_re_aggregate_symbol_trades", new_callable=AsyncMock),
            patch.object(service, "_invalidate_price_cache_for_symbol", new_callable=AsyncMock),
        ):
            result = await service.create_corporate_action(
                CorporateActionCreate(
                    symbol="OTLK",
                    date=date(2023, 5, 1),
                    ratio=Decimal("0.05"),
                    old_conid="357194941",
                    new_conid="690184975",
                ),
                user_id,
            )

        assert isinstance(result, CorporateActionRead)
        assert result.symbol == "OTLK"
        assert result.ratio == Decimal("0.05")
        assert result.old_conid == "357194941"
        assert result.new_conid == "690184975"

    @pytest.mark.unit
    async def test_create_conflict_raises_conflict_error(self, service: CorporateActionService) -> None:
        user_id = uuid.uuid4()
        existing = _make_ca(user_id=user_id)
        with patch(
            f"{_REPO}.find_by_user_symbol_date",
            new_callable=AsyncMock,
            return_value=existing,
        ):
            with pytest.raises(CorporateActionConflictError):
                await service.create_corporate_action(
                    CorporateActionCreate(
                        symbol=existing.symbol,
                        date=existing.date,
                        ratio=existing.ratio,
                        old_conid=existing.old_conid,
                        new_conid=existing.new_conid,
                    ),
                    user_id,
                )

    @pytest.mark.unit
    async def test_create_rolls_back_when_reaggregation_fails(
        self,
        service: CorporateActionService,
        mock_session: AsyncMock,
    ) -> None:
        user_id = uuid.uuid4()
        created = _make_ca(user_id=user_id)
        with (
            patch(
                f"{_REPO}.find_by_user_symbol_date",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                f"{_REPO}.create",
                new_callable=AsyncMock,
                return_value=created,
            ),
            patch.object(
                service,
                "_re_aggregate_symbol_trades",
                new_callable=AsyncMock,
                side_effect=RuntimeError("boom"),
            ),
            patch.object(service, "_invalidate_price_cache_for_symbol", new_callable=AsyncMock),
            pytest.raises(RuntimeError, match="boom"),
        ):
            await service.create_corporate_action(
                CorporateActionCreate(
                    symbol=created.symbol,
                    date=created.date,
                    ratio=created.ratio,
                    old_conid=created.old_conid,
                    new_conid=created.new_conid,
                ),
                user_id,
            )

        mock_session.rollback.assert_awaited_once()
        mock_session.commit.assert_not_called()


# ── TestUpdateCorporateAction ──────────────────────────────────────────────────


class TestUpdateCorporateAction:
    """Unit tests for :meth:`CorporateActionService.update_corporate_action`."""

    @pytest.mark.unit
    async def test_returns_updated_corporate_action_read(
        self, service: CorporateActionService
    ) -> None:
        """update_corporate_action should return the updated CorporateActionRead DTO."""
        ca = _make_ca(symbol="OTLK", ratio=Decimal("0.05"))
        updated_ca = _make_ca(
            id=ca.id,  # type: ignore[arg-type]
            user_id=ca.user_id,  # type: ignore[arg-type]
            symbol="OTLK",
            ratio=Decimal("2.0"),
        )
        with (
            patch(
                f"{_REPO}.get_by_id",
                new_callable=AsyncMock,
                return_value=ca,
            ),
            patch(
                f"{_REPO}.update",
                new_callable=AsyncMock,
                return_value=updated_ca,
            ),
            patch(
                f"{_REPO}.find_by_user_symbol_date",
                new_callable=AsyncMock,
                return_value=updated_ca,
            ),
            patch.object(service, "_re_aggregate_symbol_trades", new_callable=AsyncMock),
            patch.object(service, "_invalidate_price_cache_for_symbol", new_callable=AsyncMock),
        ):
            result = await service.update_corporate_action(
                ca.id,  # type: ignore[arg-type]
                CorporateActionUpdate(ratio=Decimal("2.0")),
                ca.user_id,  # type: ignore[arg-type]
            )

        assert isinstance(result, CorporateActionRead)
        assert result.ratio == Decimal("2.0")

    @pytest.mark.unit
    async def test_update_conflict_raises_conflict_error(
        self, service: CorporateActionService
    ) -> None:
        ca = _make_ca(symbol="OTLK", ratio=Decimal("0.05"))
        updated_ca = _make_ca(
            id=ca.id,  # type: ignore[arg-type]
            user_id=ca.user_id,  # type: ignore[arg-type]
            symbol="OTLK",
            ratio=Decimal("2.0"),
        )
        conflict = _make_ca(symbol="OTLK", ratio=Decimal("1.5"))
        with (
            patch(
                f"{_REPO}.get_by_id",
                new_callable=AsyncMock,
                return_value=ca,
            ),
            patch(
                f"{_REPO}.update",
                new_callable=AsyncMock,
                return_value=updated_ca,
            ),
            patch(
                f"{_REPO}.find_by_user_symbol_date",
                new_callable=AsyncMock,
                return_value=conflict,
            ),
        ):
            with pytest.raises(CorporateActionConflictError):
                await service.update_corporate_action(
                    ca.id,  # type: ignore[arg-type]
                    CorporateActionUpdate(ratio=Decimal("2.0")),
                    ca.user_id,  # type: ignore[arg-type]
                )

    @pytest.mark.unit
    async def test_raises_not_found_when_missing(
        self, service: CorporateActionService
    ) -> None:
        """update_corporate_action should raise CorporateActionNotFoundError
        when record is absent."""
        with (
            patch(
                f"{_REPO}.get_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
            pytest.raises(CorporateActionNotFoundError),
        ):
            await service.update_corporate_action(
                uuid.uuid4(),
                CorporateActionUpdate(ratio=Decimal("2.0")),
                uuid.uuid4(),
            )

    @pytest.mark.unit
    async def test_update_date_invalidates_symbol_cache(self, service: CorporateActionService) -> None:
        ca = _make_ca(symbol="OTLK", ratio=Decimal("0.05"))
        updated_ca = _make_ca(
            id=ca.id,  # type: ignore[arg-type]
            user_id=ca.user_id,  # type: ignore[arg-type]
            symbol="OTLK",
            action_date=date(2023, 6, 1),
            ratio=ca.ratio,
        )
        with (
            patch(f"{_REPO}.get_by_id", new_callable=AsyncMock, return_value=ca),
            patch(f"{_REPO}.update", new_callable=AsyncMock, return_value=updated_ca),
            patch(f"{_REPO}.find_by_user_symbol_date", new_callable=AsyncMock, return_value=updated_ca),
            patch.object(service, "_re_aggregate_symbol_trades", new_callable=AsyncMock),
            patch.object(service, "_invalidate_price_cache_for_symbol", new_callable=AsyncMock) as invalidate,
        ):
            await service.update_corporate_action(
                ca.id,  # type: ignore[arg-type]
                CorporateActionUpdate(date=date(2023, 6, 1)),
                ca.user_id,  # type: ignore[arg-type]
            )

        assert invalidate.await_count == 2
        invalidate.assert_awaited_with("OTLK")

    @pytest.mark.unit
    async def test_update_rolls_back_when_reaggregation_fails(
        self,
        service: CorporateActionService,
        mock_session: AsyncMock,
    ) -> None:
        ca = _make_ca(symbol="OTLK", ratio=Decimal("0.05"))
        updated_ca = _make_ca(
            id=ca.id,  # type: ignore[arg-type]
            user_id=ca.user_id,  # type: ignore[arg-type]
            symbol="OTLK",
            ratio=Decimal("2.0"),
        )
        with (
            patch(f"{_REPO}.get_by_id", new_callable=AsyncMock, return_value=ca),
            patch(f"{_REPO}.update", new_callable=AsyncMock, return_value=updated_ca),
            patch(f"{_REPO}.find_by_user_symbol_date", new_callable=AsyncMock, return_value=updated_ca),
            patch.object(
                service,
                "_re_aggregate_symbol_trades",
                new_callable=AsyncMock,
                side_effect=RuntimeError("boom"),
            ),
            patch.object(service, "_invalidate_price_cache_for_symbol", new_callable=AsyncMock),
            pytest.raises(RuntimeError, match="boom"),
        ):
            await service.update_corporate_action(
                ca.id,  # type: ignore[arg-type]
                CorporateActionUpdate(ratio=Decimal("2.0")),
                ca.user_id,  # type: ignore[arg-type]
            )

        mock_session.rollback.assert_awaited_once()
        mock_session.commit.assert_not_called()


# ── TestDeleteCorporateAction ──────────────────────────────────────────────────


class TestDeleteCorporateAction:
    """Unit tests for :meth:`CorporateActionService.delete_corporate_action`."""

    @pytest.mark.unit
    async def test_delete_calls_repo_delete(
        self, service: CorporateActionService
    ) -> None:
        """delete_corporate_action should call the repository delete method
        with the ORM object."""
        ca = _make_ca()
        mock_delete = AsyncMock()
        with (
            patch(
                f"{_REPO}.get_by_id",
                new_callable=AsyncMock,
                return_value=ca,
            ),
            patch(
                f"{_REPO}.delete",
                new=mock_delete,
            ),
            patch.object(service, "_re_aggregate_symbol_trades", new_callable=AsyncMock),
        ):
            await service.delete_corporate_action(
                ca.id,  # type: ignore[arg-type]
                ca.user_id,  # type: ignore[arg-type]
            )

        mock_delete.assert_awaited_once_with(ca)

    @pytest.mark.unit
    async def test_raises_not_found_when_missing(
        self, service: CorporateActionService
    ) -> None:
        """delete_corporate_action should raise CorporateActionNotFoundError
        when record is absent."""
        with (
            patch(
                f"{_REPO}.get_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
            pytest.raises(CorporateActionNotFoundError),
        ):
            await service.delete_corporate_action(uuid.uuid4(), uuid.uuid4())

    @pytest.mark.unit
    async def test_delete_rolls_back_when_reaggregation_fails(
        self,
        service: CorporateActionService,
        mock_session: AsyncMock,
    ) -> None:
        ca = _make_ca()
        with (
            patch(f"{_REPO}.get_by_id", new_callable=AsyncMock, return_value=ca),
            patch(f"{_REPO}.delete", new_callable=AsyncMock),
            patch.object(
                service,
                "_re_aggregate_symbol_trades",
                new_callable=AsyncMock,
                side_effect=RuntimeError("boom"),
            ),
            patch.object(service, "_invalidate_price_cache_for_symbol", new_callable=AsyncMock),
            pytest.raises(RuntimeError, match="boom"),
        ):
            await service.delete_corporate_action(
                ca.id,  # type: ignore[arg-type]
                ca.user_id,  # type: ignore[arg-type]
            )

        mock_session.rollback.assert_awaited_once()
        mock_session.commit.assert_not_called()
