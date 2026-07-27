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

"""Business logic for logical execution lifecycle and trade re-aggregation."""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BrokerRawTransactionNotFoundError,
    ExecutionNotFoundError,
    ExecutionValidationError,
    TradeNotFoundError,
)
from app.models.corporate_action import CorporateAction
from app.models.logical_execution import (
    EXECUTION_ORIGIN_IMPORTED,
    EXECUTION_ORIGIN_MANUAL,
    EXECUTION_ORIGIN_MERGED,
    EXECUTION_ORIGIN_SPLIT,
    LogicalExecution,
)
from app.repositories.broker_raw_transaction_repository import BrokerRawTransactionRepository
from app.repositories.execution import ExecutionRepository
from app.repositories.trade_repository import TradeRepository
from app.schemas.execution import (
    LinkBrokerTransactionResponse,
    LogicalExecutionCreate,
    LogicalExecutionRead,
    LogicalExecutionUpdate,
    MergeExecutionsRequest,
    MergeExecutionsResponse,
    SplitExecutionRequest,
    SplitExecutionResponse,
)
from app.services.audit_service import AuditEventService
from app.services.corporate_action_service import CorporateActionService
from app.utils.conflict_detection import detect_duplicate_pairs
from app.utils.split_adjust import split_adjust_execution_values

if TYPE_CHECKING:
    from app.models.broker_raw_transaction import BrokerRawTransaction
    from app.models.trade import Trade


class ExecutionService:
    """Service layer for LogicalExecutions containing business logic."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the ExecutionService.

        Args:
            session: SQLAlchemy async session.
        """
        self.session = session
        self.execution_repo = ExecutionRepository(session)
        self.trade_repo = TradeRepository(session)
        self.raw_transaction_repo = BrokerRawTransactionRepository(session)
        self.corporate_action_service = CorporateActionService(session)
        self._audit = AuditEventService()

    async def list_for_trade(
        self,
        trade_id: uuid.UUID,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID | None = None,
        include_deleted: bool = False,
    ) -> Sequence[LogicalExecutionRead]:
        """List executions for a specific trade, ensuring user ownership.

        Args:
            trade_id: The target trade ID.
            user_id: The authenticated user's ID.
            include_deleted: When True, include soft-deleted executions.

        Returns:
            A sequence of logical executions.

        Raises:
            TradeNotFoundError: If the trade is not found or user lacks access.
        """
        trade = await self.trade_repo.get_by_id(trade_id, user_id, portfolio_id)
        if not trade:
            raise TradeNotFoundError("Trade not found.")

        executions = await self.execution_repo.list_by_trade_id(
            trade_id,
            include_deleted=include_deleted,
        )
        corporate_actions_by_key: dict[tuple[str, str | None], list[CorporateAction]] = {}
        for execution in executions:
            key = (execution.symbol, execution.conid)
            if key in corporate_actions_by_key:
                continue
            corporate_actions_by_key[key] = await self.corporate_action_service.list_for_execution(
                user_id,
                symbol=execution.symbol,
                conid=execution.conid,
            )

        result: list[LogicalExecutionRead] = []
        for execution in executions:
            raw_price = execution.price
            raw_quantity = execution.quantity
            adjusted_price, adjusted_quantity = split_adjust_execution_values(
                raw_price=raw_price,
                raw_quantity=raw_quantity,
                executed_at=execution.executed_at,
                symbol=execution.symbol,
                conid=execution.conid,
                corporate_actions=corporate_actions_by_key[(execution.symbol, execution.conid)],
            )

            payload = {
                column.name: getattr(execution, column.name)
                for column in execution.__table__.columns
            }
            payload["price"] = adjusted_price
            payload["quantity"] = adjusted_quantity
            payload["raw_price"] = raw_price
            payload["raw_quantity"] = raw_quantity
            result.append(LogicalExecutionRead.model_validate(payload))

        return result

    async def create_manual_execution(
        self,
        trade_id: uuid.UUID,
        user_id: uuid.UUID,
        data: LogicalExecutionCreate,
        portfolio_id: uuid.UUID | None = None,
    ) -> LogicalExecution:
        """Create a manual execution under a specific trade.

        Args:
            trade_id: Target trade ID.
            user_id: User ownership check.
            data: Payload with execution details.

        Returns:
            The created logical execution.

        Raises:
            TradeNotFoundError: If the trade is not found.
        """
        trade = await self.trade_repo.get_by_id(trade_id, user_id, portfolio_id)
        if not trade:
            raise TradeNotFoundError("Trade not found.")

        leg_asset_class = trade.asset_class
        leg_multiplier = trade.multiplier
        if trade.is_combo:
            if data.asset_class is not None:
                leg_asset_class = data.asset_class
            if data.multiplier is not None:
                leg_multiplier = data.multiplier
        if leg_asset_class is None:
            raise ExecutionValidationError("asset_class is required for execution legs on COMBO trades.")

        # Create with origin=manual and copy instrument props from trade
        payload = data.model_dump(
            exclude_unset=True,
            exclude={"asset_class", "multiplier"},
        )
        execution = await self.execution_repo.create(
            user_id=user_id,
            account_id=trade.account_id,
            symbol=trade.symbol,
            asset_class=leg_asset_class,
            currency=trade.currency,
            multiplier=leg_multiplier,
            origin=EXECUTION_ORIGIN_MANUAL,
            trade_id=trade_id,
            **payload,
        )

        await self._re_aggregate_trade(trade_id, user_id)
        await self.session.commit()
        return execution

    async def update_execution(
        self,
        execution_id: uuid.UUID,
        user_id: uuid.UUID,
        data: LogicalExecutionUpdate,
        portfolio_id: uuid.UUID | None = None,
    ) -> LogicalExecution:
        """Update an execution by ID and re-aggregate its parent trade.

        When the execution has ``origin='imported'``, ``'split'``, or
        ``'merged'`` and the patch contains at least one mutating field,
        automatically sets ``user_modified=True`` (see the
        ``execution-overwrite-protection`` spec).  ``origin='manual'``
        executions are never marked.

        Args:
            execution_id: Target execution ID.
            user_id: The requesting user's ID.
            data: Payload containing update fields.
            portfolio_id: Optional portfolio scope for ownership isolation.

        Returns:
            The updated logical execution.

        Raises:
            ExecutionNotFoundError: If execution is not found or not owned by user.
        """
        execution = await self.execution_repo.get_by_id(execution_id, user_id)
        if not execution:
            raise ExecutionNotFoundError("Execution not found.")
        if execution.trade_id is not None:
            trade = await self.trade_repo.get_by_id(
                execution.trade_id,
                user_id,
                portfolio_id,
            )
            if trade is None:
                raise ExecutionNotFoundError("Execution not found.")

        update_data = data.model_dump(exclude_unset=True)

        # Execution-overwrite-protection: mark PATCHes on all editable origins
        # (imported | split | merged) so the import pipeline preserves them.
        # Manual executions are user-owned by construction and never marked.
        # A no-op patch (no mutating fields) leaves the marker untouched.
        if update_data and execution.origin in (
            EXECUTION_ORIGIN_IMPORTED,
            EXECUTION_ORIGIN_SPLIT,
            EXECUTION_ORIGIN_MERGED,
        ):
            update_data["user_modified"] = True

        execution = await self.execution_repo.update(execution, **update_data)
        if execution.trade_id:
            await self._re_aggregate_trade(execution.trade_id, user_id)

        await self.session.commit()
        return execution

    async def delete_execution(
        self,
        execution_id: uuid.UUID,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID | None = None,
    ) -> LogicalExecution | None:
        """Delete an execution following Decision 4 rules.

        - ``imported|merged|split`` → soft-delete (``deleted=True``), return execution
        - ``manual`` → hard-delete (row removed), return None
        - Already soft-deleted → raise ExecutionValidationError (409)

        After delete, the parent trade is re-aggregated.

        Args:
            execution_id: Execution to delete.
            user_id: User ownership check.
            portfolio_id: Optional portfolio scope for ownership isolation.

        Returns:
            The soft-deleted execution (for imported/merged/split), or None (manual).

        Raises:
            ExecutionNotFoundError: If execution is not found or not owned by user.
            ExecutionValidationError: If execution is already soft-deleted.
        """
        execution = await self.execution_repo.get_by_id(execution_id, user_id)
        if not execution:
            raise ExecutionNotFoundError("Execution not found.")
        if execution.trade_id is not None:
            trade = await self.trade_repo.get_by_id(
                execution.trade_id,
                user_id,
                portfolio_id,
            )
            if trade is None:
                raise ExecutionNotFoundError("Execution not found.")

        # Decision 4: already deleted → 409 Conflict
        if execution.deleted:
            raise ExecutionValidationError("Execution is already deleted. Use restore to undo.")

        trade_id = execution.trade_id

        if execution.origin == EXECUTION_ORIGIN_MANUAL:
            # Hard-delete: row removed, return None (→ 204 No Content).
            #
            # Execution-overwrite-protection: when the manual execution is
            # linked to a broker raw transaction (source_id set), atomically
            # release it (suppressed=False) in the same transaction so the
            # original imported leg can re-materialise on the next import.
            # Unlinked manuals (source_id NULL) leave BRTs untouched.
            released_source_id = execution.source_id
            await self.execution_repo.delete(execution_id)
            if released_source_id is not None:
                await self.raw_transaction_repo.set_suppressed(released_source_id, False)
            if trade_id:
                remaining = await self.execution_repo.list_by_trade_id(trade_id, include_deleted=False)
                if not remaining:
                    # Trade is now empty — cascade-delete it
                    trade_to_delete = await self.trade_repo.get_by_id(
                        trade_id,
                        user_id,
                        portfolio_id,
                    )
                    if trade_to_delete:
                        await self.trade_repo.delete(trade_to_delete)
                else:
                    await self._re_aggregate_trade(trade_id, user_id)
            self._audit.create_audit_event(
                action="execution.deleted",
                user_id=user_id,
                email=None,
                resource_type="execution",
                resource_id=execution_id,
                ip_address=None,
                user_agent=None,
                request_id=str(uuid.uuid4()),
                status_code=204,
                method="DELETE",
                path="/executions",
                metadata=(
                    {"released_source_id": released_source_id}
                    if released_source_id is not None
                    else {}
                ),
            )
            await self.session.commit()
            return None
        else:
            # Soft-delete: imported|merged|split → set deleted=True, return (→ 200)
            await self.execution_repo.soft_delete(execution_id)
            # Reload the updated execution
            updated = await self.execution_repo.get_by_id(execution_id)
            if trade_id:
                await self._re_aggregate_trade(trade_id, user_id)
            await self.session.commit()
            return updated

    async def list_broker_transactions(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID | None = None,
        symbol: str | None = None,
    ) -> Sequence["BrokerRawTransaction"]:
        """List broker raw transactions for the manual-link picker.

        Args:
            user_id: The requesting user's ID (ownership scope).
            account_id: Optional account filter.
            symbol: Optional exact ticker-symbol filter.

        Returns:
            Broker raw transactions owned by the user, newest-aware ordering
            (executed_at ascending, matching the repository default).
        """
        return await self.raw_transaction_repo.list_by_user(
            user_id=user_id,
            account_id=account_id,
            symbol=symbol,
        )

    async def link_broker_transaction(
        self,
        execution_id: uuid.UUID,
        raw_transaction_id: str,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID | None = None,
    ) -> LinkBrokerTransactionResponse:
        """Link a manual execution to a broker raw transaction.

        Sets ``LogicalExecution.source_id`` to the raw transaction ID and marks
        the raw transaction ``suppressed=True`` so future imports skip it —
        the manual execution is the stand-in for the broker fill. Both writes
        commit in the same database transaction.

        Business rules (see the ``execution-overwrite-protection`` spec):
        - ``origin != 'manual'`` → 409 Conflict.
        - Raw transaction not owned by ``user_id`` → 404 Not Found.
        - Raw transaction already referenced by another execution's
          ``source_id`` → 409 Conflict (no implicit relink).

        Args:
            execution_id: The manual execution to link.
            raw_transaction_id: Primary key of the target BrokerRawTransaction.
            user_id: The requesting user's ID.
            portfolio_id: Optional portfolio scope for ownership isolation.

        Returns:
            The updated execution wrapped in a response payload.

        Raises:
            ExecutionNotFoundError: If execution is not found or not owned by user.
            ExecutionValidationError: If origin is not ``manual`` or the raw
                transaction is already linked (409 semantics).
            BrokerRawTransactionNotFoundError: If the raw transaction is not
                found for this user (404 semantics).
        """
        execution = await self.execution_repo.get_by_id(execution_id, user_id)
        if not execution:
            raise ExecutionNotFoundError("Execution not found.")
        if execution.trade_id is not None:
            trade = await self.trade_repo.get_by_id(
                execution.trade_id,
                user_id,
                portfolio_id,
            )
            if trade is None:
                raise ExecutionNotFoundError("Execution not found.")

        if execution.origin != EXECUTION_ORIGIN_MANUAL:
            raise ExecutionValidationError(
                f"Only manual executions can be linked to a broker transaction (origin='{execution.origin}')."
            )

        raw = await self.raw_transaction_repo.get_by_id_for_user(raw_transaction_id, user_id)
        if raw is None:
            raise BrokerRawTransactionNotFoundError("Broker transaction not found.")

        existing_link = await self.execution_repo.get_by_source_id(
            raw_transaction_id,
            exclude_execution_id=execution.id,
        )
        if existing_link is not None:
            raise ExecutionValidationError(
                f"Broker transaction is already linked to execution {existing_link.id}. Delete that link first."
            )

        # Atomic: point the manual execution at the BRT and suppress the BRT
        # so future imports do not re-materialise the original imported leg.
        execution.source_id = raw_transaction_id
        try:
            await self.session.flush()
        except IntegrityError:
            await self.session.rollback()
            raise ExecutionValidationError(
                "Broker transaction is already linked to another execution. Delete that link first."
            )
        await self.raw_transaction_repo.set_suppressed(raw_transaction_id, True)

        # Linking resolves a potential unlinked-duplicate conflict — re-aggregate.
        if execution.trade_id:
            await self._re_aggregate_trade(execution.trade_id, user_id)

        self._audit.create_audit_event(
            action="execution.linked_to_broker_transaction",
            user_id=user_id,
            email=None,
            resource_type="execution",
            resource_id=execution_id,
            ip_address=None,
            user_agent=None,
            request_id=str(uuid.uuid4()),
            status_code=200,
            method="POST",
            path="/executions/link-broker-transaction",
            metadata={
                "execution_id": str(execution_id),
                "raw_transaction_id": raw_transaction_id,
            },
        )

        await self.session.commit()
        return LinkBrokerTransactionResponse(
            execution=LogicalExecutionRead.model_validate(execution),
            message="Execution linked to broker transaction.",
        )

    async def restore_execution(
        self,
        execution_id: uuid.UUID,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID | None = None,
    ) -> LogicalExecution:
        """Restore a soft-deleted execution.

        Sets ``deleted=False`` and re-aggregates the parent trade.

        Args:
            execution_id: Execution to restore.
            user_id: User ownership check.
            portfolio_id: Optional portfolio scope for ownership isolation.

        Returns:
            The restored execution.

        Raises:
            ExecutionNotFoundError: If execution is not found or not owned by user.
            ExecutionValidationError: If execution is not soft-deleted.
        """
        execution = await self.execution_repo.get_by_id(execution_id, user_id)
        if not execution:
            raise ExecutionNotFoundError("Execution not found.")
        if execution.trade_id is not None:
            trade = await self.trade_repo.get_by_id(
                execution.trade_id,
                user_id,
                portfolio_id,
            )
            if trade is None:
                raise ExecutionNotFoundError("Execution not found.")

        if not execution.deleted:
            raise ExecutionValidationError("Execution is not deleted. Only soft-deleted executions can be restored.")

        await self.execution_repo.restore(execution_id)
        updated = await self.execution_repo.get_by_id(execution_id)
        if updated is None:
            raise ExecutionNotFoundError("Execution not found after restore.")

        if updated.trade_id:
            await self._re_aggregate_trade(updated.trade_id, user_id)

        await self.session.commit()
        return updated

    async def split_execution(
        self,
        execution_id: uuid.UUID,
        user_id: uuid.UUID,
        data: SplitExecutionRequest,
        portfolio_id: uuid.UUID | None = None,
    ) -> SplitExecutionResponse:
        """Split an execution into two child executions.

        Decision 3: Mark original ``deleted=True``, create two children with
        ``origin='split'`` and ``parent_id=original.id``.

        The sum of ``quantity_a + quantity_b`` must equal the original quantity.

        Args:
            execution_id: Execution to split.
            user_id: User ownership check.
            data: Split parameters (quantities, optional prices/timestamps).
            portfolio_id: Optional portfolio scope for ownership isolation.

        Returns:
            A :class:`SplitExecutionResponse` with both new executions and the original.

        Raises:
            ExecutionNotFoundError: If execution is not found or not owned by user.
            ExecutionValidationError: If the execution cannot be split (deleted,
                wrong origin, or quantity mismatch).
        """
        execution = await self.execution_repo.get_by_id(execution_id, user_id)
        if not execution:
            raise ExecutionNotFoundError("Execution not found.")
        if execution.trade_id is not None:
            trade = await self.trade_repo.get_by_id(
                execution.trade_id,
                user_id,
                portfolio_id,
            )
            if trade is None:
                raise ExecutionNotFoundError("Execution not found.")

        if execution.deleted:
            raise ExecutionValidationError("Cannot split a deleted execution.")

        if execution.origin not in (EXECUTION_ORIGIN_IMPORTED, EXECUTION_ORIGIN_MANUAL):
            raise ExecutionValidationError(f"Cannot split an execution with origin='{execution.origin}'. Only imported or manual executions can be split.")

        # Validate quantity sum
        _TOLERANCE = Decimal("0.0000001")
        if abs(data.quantity_a + data.quantity_b - execution.quantity) > _TOLERANCE:
            raise ExecutionValidationError(
                f"quantity_a ({data.quantity_a}) + quantity_b ({data.quantity_b}) must equal original quantity ({execution.quantity})."
            )

        # Soft-delete the original
        await self.execution_repo.soft_delete(execution_id)

        # Create child A
        exec_a = await self.execution_repo.create(
            user_id=execution.user_id,
            account_id=execution.account_id,
            symbol=execution.symbol,
            conid=execution.conid,
            asset_class=execution.asset_class,
            direction=execution.direction,
            quantity=data.quantity_a,
            price=data.price_a if data.price_a is not None else execution.price,
            commission=execution.commission * (data.quantity_a / execution.quantity),
            executed_at=(data.executed_at_a if data.executed_at_a is not None else execution.executed_at),
            pnl=None,
            currency=execution.currency,
            multiplier=execution.multiplier,
            origin=EXECUTION_ORIGIN_SPLIT,
            parent_id=execution.id,
            trade_id=execution.trade_id,
        )

        # Create child B
        exec_b = await self.execution_repo.create(
            user_id=execution.user_id,
            account_id=execution.account_id,
            symbol=execution.symbol,
            conid=execution.conid,
            asset_class=execution.asset_class,
            direction=execution.direction,
            quantity=data.quantity_b,
            price=data.price_b if data.price_b is not None else execution.price,
            commission=execution.commission * (data.quantity_b / execution.quantity),
            executed_at=(data.executed_at_b if data.executed_at_b is not None else execution.executed_at),
            pnl=None,
            currency=execution.currency,
            multiplier=execution.multiplier,
            origin=EXECUTION_ORIGIN_SPLIT,
            parent_id=execution.id,
            trade_id=execution.trade_id,
        )

        # Reload the original with updated fields
        original = await self.execution_repo.get_by_id(execution_id)
        if original is None:
            raise ExecutionNotFoundError("Original execution not found after split.")

        if execution.trade_id:
            await self._re_aggregate_trade(execution.trade_id, user_id)

        await self.session.commit()

        return SplitExecutionResponse(
            execution_a=LogicalExecutionRead.model_validate(exec_a),
            execution_b=LogicalExecutionRead.model_validate(exec_b),
            original=LogicalExecutionRead.model_validate(original),
        )

    async def merge_executions(
        self,
        user_id: uuid.UUID,
        data: MergeExecutionsRequest,
        portfolio_id: uuid.UUID | None = None,
    ) -> MergeExecutionsResponse:
        """Merge two or more executions into a single execution.

        Decision: Mark all source executions ``deleted=True``, then create a
        merged execution with ``origin='merged'`` and ``parent_id=primary.id``.

        The merged quantity is the sum of all source quantities.  The merged
        price defaults to the weighted-average price of the sources.

        All source executions must:
        - Belong to ``user_id``.
        - Have the same ``trade_id``, ``symbol``, ``direction``.
        - Not already be deleted.
        - Include the ``primary_id`` in ``execution_ids``.

        Args:
            user_id: User ownership check.
            data: Merge parameters.
            portfolio_id: Optional portfolio scope for ownership isolation.

        Returns:
            A :class:`MergeExecutionsResponse` with the merged execution and
            the soft-deleted source executions.

        Raises:
            ExecutionNotFoundError: If any execution is not found or not
                owned by the user.
            ExecutionValidationError: If validations fail (deleted sources,
                mismatched trade/symbol/direction, or primary_id not included).
        """
        if data.primary_id not in data.execution_ids:
            raise ExecutionValidationError("primary_id must be included in execution_ids.")

        # Load all source executions
        sources: list[LogicalExecution] = []
        for ex_id in data.execution_ids:
            ex = await self.execution_repo.get_by_id(ex_id, user_id)
            if ex is None:
                raise ExecutionNotFoundError(f"Execution {ex_id} not found.")
            if ex.deleted:
                raise ExecutionValidationError(f"Execution {ex_id} is already deleted and cannot be merged.")
            sources.append(ex)

        primary = next(ex for ex in sources if ex.id == data.primary_id)

        # Validate that all sources share the same trade, symbol, and direction
        first_trade_id = sources[0].trade_id
        first_symbol = sources[0].symbol
        first_direction = sources[0].direction
        for ex in sources[1:]:
            if ex.trade_id != first_trade_id:
                raise ExecutionValidationError("All executions must belong to the same trade.")
            if ex.symbol != first_symbol:
                raise ExecutionValidationError("All executions must have the same symbol.")
            if ex.direction != first_direction:
                raise ExecutionValidationError("All executions must have the same direction.")

        if first_trade_id is not None:
            trade = await self.trade_repo.get_by_id(
                first_trade_id,
                user_id,
                portfolio_id,
            )
            if trade is None:
                raise ExecutionNotFoundError("Execution not found.")

        # Compute merged quantity (sum) and weighted-average price
        total_quantity = sum((ex.quantity for ex in sources), Decimal("0"))
        if data.price is not None:
            merged_price = data.price
        else:
            total_value = sum((ex.quantity * ex.price for ex in sources), Decimal("0"))
            merged_price = total_value / total_quantity if total_quantity > Decimal("0") else primary.price
        merged_commission = sum((ex.commission for ex in sources), Decimal("0"))
        merged_executed_at = data.executed_at if data.executed_at is not None else primary.executed_at

        # Soft-delete all source executions
        for ex in sources:
            await self.execution_repo.soft_delete(ex.id)

        # Create the merged execution
        merged = await self.execution_repo.create(
            user_id=primary.user_id,
            account_id=primary.account_id,
            symbol=primary.symbol,
            conid=primary.conid,
            asset_class=primary.asset_class,
            direction=primary.direction,
            quantity=total_quantity,
            price=merged_price,
            commission=merged_commission,
            executed_at=merged_executed_at,
            pnl=None,
            currency=primary.currency,
            multiplier=primary.multiplier,
            origin=EXECUTION_ORIGIN_MERGED,
            parent_id=primary.id,
            trade_id=primary.trade_id,
        )

        # Reload the soft-deleted sources to return updated state
        reloaded_sources: list[LogicalExecution] = []
        for ex in sources:
            reloaded = await self.execution_repo.get_by_id(ex.id)
            if reloaded is not None:
                reloaded_sources.append(reloaded)

        if primary.trade_id:
            await self._re_aggregate_trade(primary.trade_id, user_id)

        await self.session.commit()

        return MergeExecutionsResponse(
            merged=LogicalExecutionRead.model_validate(merged),
            sources=[LogicalExecutionRead.model_validate(s) for s in reloaded_sources],
        )

    async def reassign_execution(
        self,
        execution_id: uuid.UUID,
        target_trade_id: uuid.UUID,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID | None = None,
    ) -> LogicalExecution:
        """Reassign an execution to another trade.

        Args:
            execution_id: Execution to reassign.
            target_trade_id: The ID of the target trade.
            user_id: User ownership check.

        Returns:
            The updated logical execution.

        Raises:
            ExecutionNotFoundError: If execution is not found or not owned by user.
            TradeNotFoundError: If target trade is not found or not owned by user.
            ExecutionValidationError: If symbol/account constraints do not match.
        """
        execution = await self.execution_repo.get_by_id(execution_id, user_id)
        if not execution:
            raise ExecutionNotFoundError("Execution not found.")

        target_trade = await self.trade_repo.get_by_id(
            target_trade_id,
            user_id,
            portfolio_id,
        )
        if not target_trade:
            raise TradeNotFoundError("Target trade not found.")

        if execution.symbol != target_trade.symbol or execution.account_id != target_trade.account_id:
            raise ExecutionValidationError("Cannot reassign: symbol or account mismatch.")

        source_trade_id = execution.trade_id

        execution = await self.execution_repo.update(execution, trade_id=target_trade_id)

        await self._re_aggregate_trade(target_trade_id, user_id)

        if source_trade_id and source_trade_id != target_trade_id:
            remaining_executions = await self.execution_repo.list_by_trade_id(source_trade_id)
            if not remaining_executions:
                source_trade = await self.trade_repo.get_by_id(source_trade_id, user_id)
                if source_trade:
                    await self.trade_repo.delete(source_trade)
            else:
                await self._re_aggregate_trade(source_trade_id, user_id)

        await self.session.commit()
        return execution

    async def detach_execution(
        self,
        execution_id: uuid.UUID,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID | None = None,
    ) -> "Trade":
        """Detach an execution from its current trade into a new trade.

        Args:
            execution_id: Execution to detach.
            user_id: User ownership check.
            portfolio_id: Optional portfolio scope for ownership isolation.

        Returns:
            The newly created Trade.

        Raises:
            ExecutionNotFoundError: If execution is not found or not owned by user.
            ExecutionValidationError: If execution cannot be detached.
        """
        from app.schemas.trade import TradeCreate

        execution = await self.execution_repo.get_by_id(execution_id, user_id)
        if not execution:
            raise ExecutionNotFoundError("Execution not found.")

        source_trade_id = execution.trade_id
        if not source_trade_id:
            raise ExecutionValidationError("Execution is not attached to a trade.")

        source_trade = await self.trade_repo.get_by_id(
            source_trade_id,
            user_id,
            portfolio_id,
        )
        if source_trade is None:
            raise ExecutionNotFoundError("Execution not found.")

        remaining_executions = await self.execution_repo.list_by_trade_id(source_trade_id)
        if len(remaining_executions) <= 1:
            raise ExecutionValidationError("Cannot detach the only execution in a trade.")

        # Create a new trade for the execution
        new_trade_data = TradeCreate(
            user_id=user_id,
            symbol=execution.symbol,
            direction=execution.direction,
            asset_class=execution.asset_class,
            quantity=execution.quantity,
            entry_price=execution.price,
            opened_at=execution.executed_at,
            commission=execution.commission,
            currency=execution.currency,
            multiplier=execution.multiplier,
            account_id=execution.account_id,
        )

        new_trade = await self.trade_repo.create(new_trade_data)

        execution = await self.execution_repo.update(execution, trade_id=new_trade.id)

        await self._re_aggregate_trade(new_trade.id, user_id)
        await self._re_aggregate_trade(source_trade_id, user_id)

        await self.session.commit()
        reloaded_new_trade = await self.trade_repo.get_by_id(
            new_trade.id,
            user_id,
            portfolio_id,
        )
        if reloaded_new_trade is None:
            raise TradeNotFoundError(f"Trade {new_trade.id} not found.")
        return reloaded_new_trade

    async def _re_aggregate_trade(
        self,
        trade_id: uuid.UUID,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID | None = None,
    ) -> None:
        """Re-aggregate a trade's values from its active logical executions.

        Only executions with ``deleted=False`` are included in the aggregation
        (Decision 5: add ``AND deleted=false`` filter to aggregator query).

        Groups executions by direction relative to the trade's direction:
        - Entry executions (same direction): compute VWAP entry_price, total quantity.
        - Exit executions (opposite direction): compute VWAP exit_price.
        - Commission = sum of all execution commissions.
        - PnL = sum of execution pnl values if available, else computed from prices.
        - Net PnL = PnL - Commission.
        - opened_at = min(executed_at) of entry executions.
        - closed_at = max(executed_at) of exit executions (if fully exited).

        Args:
            trade_id: Target trade ID to re-aggregate.
            user_id: For permissions check.
        """
        trade = await self.trade_repo.get_by_id(trade_id, user_id, portfolio_id)
        if not trade:
            return

        # Decision 5: filter to only non-deleted executions
        executions = await self.execution_repo.list_by_trade_id(trade_id, include_deleted=False)
        if not executions:
            # Empty trade cannot have a duplicate conflict (defensive reset).
            if trade.has_conflict:
                trade.has_conflict = False
                await self.session.flush()
            return

        # Execution-overwrite-protection: authoritative recompute of the
        # unlinked-duplicate conflict flag on every rebuild — always set,
        # never merged. Editing, deleting, or manually-linking a leg flows
        # through here, so the flag auto-clears when the duplicate disappears.
        trade.has_conflict = detect_duplicate_pairs(executions)

        from app.models.trade import (
            Direction,
        )

        is_long = trade.direction == Direction.LONG

        entry_qty = Decimal(0)
        entry_cost = Decimal(0)
        exit_qty = Decimal(0)
        exit_cost = Decimal(0)
        total_commission = Decimal(0)
        total_pnl: Decimal | None = Decimal(0)
        has_broker_pnl = False

        entry_times: list[datetime] = []
        exit_times: list[datetime] = []

        for ex in executions:
            total_commission += ex.commission

            is_entry = (is_long and ex.direction == Direction.LONG) or (not is_long and ex.direction == Direction.SHORT)

            if is_entry:
                entry_qty += ex.quantity
                entry_cost += ex.quantity * ex.price
                entry_times.append(ex.executed_at)
            else:
                exit_qty += ex.quantity
                exit_cost += ex.quantity * ex.price
                exit_times.append(ex.executed_at)

            # Accumulate broker-reported PnL when available
            if ex.pnl is not None:
                has_broker_pnl = True
                if total_pnl is not None:
                    total_pnl += ex.pnl

        _PRECISION = Decimal("0.0000000001")
        if trade.is_combo:
            trade.entry_price = None
            trade.exit_price = None
            trade.quantity = None
            trade.commission = total_commission
            if executions:
                opened_values = [ex.executed_at for ex in executions]
                trade.opened_at = min(opened_values)
                trade.closed_at = max(opened_values)
            else:
                trade.closed_at = None

            if has_broker_pnl and total_pnl is not None:
                trade.pnl = total_pnl.quantize(_PRECISION).normalize()
            else:
                trade.pnl = None

            if trade.pnl is not None:
                trade.net_pnl = (trade.pnl - total_commission).quantize(_PRECISION).normalize()
            else:
                trade.net_pnl = None
        else:
            # --- Compute derived fields ---
            trade.quantity = entry_qty
            trade.entry_price = entry_cost / entry_qty if entry_qty > 0 else Decimal(0)
            trade.exit_price = exit_cost / exit_qty if exit_qty > 0 else None
            trade.commission = total_commission

            # opened_at = earliest entry execution
            if entry_times:
                trade.opened_at = min(entry_times)

            # closed_at = latest exit execution, only if fully exited
            if exit_qty >= entry_qty and entry_qty > 0 and exit_times:
                trade.closed_at = max(exit_times)
            else:
                trade.closed_at = None

            # PnL: prefer sum of broker-reported pnl, else compute from prices
            # Round to 10 decimal places to avoid accumulating precision drift from
            # repeating-decimal VWAP prices (e.g. 23000/150 = 153.333...).
            if exit_qty > 0 and trade.exit_price is not None:
                if has_broker_pnl and total_pnl is not None:
                    trade.pnl = total_pnl.quantize(_PRECISION).normalize()
                else:
                    multiplier = Decimal(trade.multiplier)
                    if is_long:
                        raw_pnl = (trade.exit_price - trade.entry_price) * exit_qty * multiplier
                    else:
                        raw_pnl = (trade.entry_price - trade.exit_price) * exit_qty * multiplier
                    trade.pnl = raw_pnl.quantize(_PRECISION).normalize()
                trade.net_pnl = (trade.pnl - total_commission).quantize(_PRECISION).normalize()
            else:
                trade.pnl = None
                trade.net_pnl = None

        trade.updated_at = datetime.now(UTC)
        await self.session.flush()

    async def re_aggregate_trade(
        self,
        trade_id: uuid.UUID,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID | None = None,
    ) -> None:
        """Public wrapper for _re_aggregate_trade.

        Args:
            trade_id: Target trade UUID.
            user_id: Owner user UUID.
        """
        await self._re_aggregate_trade(trade_id, user_id, portfolio_id)
