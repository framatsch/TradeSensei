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

"""Business-logic service for broker file import operations.

Orchestrates broker file parsing and bulk trade creation for a given
account.  No HTTP concepts appear in this layer.
"""

import asyncio
import json
import logging
import tracemalloc
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from datetime import datetime
from decimal import Decimal
from functools import lru_cache
from time import perf_counter
from typing import cast

from sqlalchemy import event
from sqlalchemy import text as sa_text
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    IMPORT_EXECUTIONS_BATCH_SIZE,
    IMPORT_MEMORY_ALERT_THRESHOLD_BYTES,
    IMPORT_RETRY_BASE_DELAY_SECONDS,
    IMPORT_RETRY_MAX_ATTEMPTS,
    MILLISECONDS_PER_SECOND,
)
from app.core.exceptions import (
    AccountNotFoundError,
    ExecutionNotFoundError,
    ExecutionValidationError,
    ImportParseError,
    TradeNotFoundError,
)
from app.models.logical_execution import (
    EXECUTION_ORIGIN_IMPORTED,
    EXECUTION_ORIGIN_SPLIT,
    LogicalExecution,
)
from app.models.trade import Direction as TradeDirection
from app.models.trade import Trade
from app.repositories.account_repository import AccountRepository
from app.repositories.broker_raw_transaction_repository import (
    BrokerRawTransactionRepository,
)
from app.repositories.corporate_action_repository import CorporateActionRepository
from app.repositories.execution import ExecutionRepository
from app.repositories.portfolio_repository import PortfolioRepository
from app.repositories.trade_repository import TradeRepository
from app.schemas.broker_raw_transaction import BrokerRawTransactionCreate
from app.schemas.corporate_action import CorporateActionCreateRequest
from app.schemas.imports import FreshStartResult, ImportResult
from app.schemas.trade import TradeCreate
from app.services.audit_service import AuditEventService, generate_request_id
from app.services.logical_execution_service import LogicalExecutionService
from app.utils.conflict_detection import detect_duplicate_pairs
from app.utils.parsers.aggregator import (
    CorporateActionLike,
    ExecutionAllocation,
    ExecutionLike,
    SeedLotLike,
    TradeCreateWithSources,
    aggregate_executions_fifo_with_sources,
    build_combo_positions,
    logical_executions_to_trade_creates,
)
from app.utils.parsers.base import BrokerParser
from app.utils.parsers.factory import BrokerType, get_parser
from app.utils.parsers.schwab_json import decode_schwab_wrapped_payload
from app.utils.schwab_account_resolution import resolve_schwab_account_entry

logger = logging.getLogger(__name__)


class ImportService:
    """Service layer for importing broker trade files.

    Validates account ownership, delegates to the appropriate broker
    parser, and bulk-creates the parsed trades.

    When the parser supports the raw-data layer
    (:meth:`~app.utils.parsers.base.BrokerParser.parse_raw`),
    the import follows a four-step pipeline:

    1. Parse raw executions →
       :class:`~app.schemas.broker_raw_transaction.BrokerRawTransactionCreate`
    2. Upsert raw records into ``broker_raw_transactions`` (idempotent).
    3. Create :class:`~app.models.logical_execution.LogicalExecution` records
       (1:1 with newly inserted raw rows).
    4. Convert logical executions → :class:`~app.schemas.trade.TradeCreate` and
       run FIFO aggregation → persist :class:`~app.models.trade.Trade` rows.

    Parsers that do not yet implement ``parse_raw`` fall back to the legacy
    path (``parse()`` returns aggregated :class:`~app.schemas.trade.TradeCreate`
    objects directly).

    Args:
        session: An open :class:`~sqlalchemy.ext.asyncio.AsyncSession`
            managed by the caller.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialise with a database session.

        Args:
            session: The session to use for all operations within this
                request.
        """
        self._session = session
        self._account_repo = AccountRepository(session)
        self._trade_repo = TradeRepository(session)
        self._ca_repo = CorporateActionRepository(session)
        self._portfolio_repo = PortfolioRepository(session)
        self._raw_repo = BrokerRawTransactionRepository(session)
        self._logical_svc = LogicalExecutionService(session)
        self._exec_repo = ExecutionRepository(session)
        self._audit = AuditEventService()

    async def set_statement_timeout(self, timeout_seconds: int) -> None:
        """Set the PostgreSQL ``statement_timeout`` for the current transaction.

        Uses ``SET LOCAL`` so the timeout is automatically reverted on
        ``COMMIT`` or ``ROLLBACK``.  A value of ``0`` disables the timeout
        (no guard applied).

        Args:
            timeout_seconds: Maximum execution time in seconds.  Pass ``0``
                to disable the timeout.
        """
        if timeout_seconds > 0:
            await self._session.execute(sa_text(f"SET LOCAL statement_timeout = '{timeout_seconds}s'"))

    async def import_file(
        self,
        content: bytes,
        filename: str,
        broker: BrokerType,
        portfolio_id: uuid.UUID,
        account_id: uuid.UUID | None,
        user_id: uuid.UUID,
        overwrite_manually_edited: bool = False,
    ) -> ImportResult:
        """Parse a broker export file and bulk-create trades for an account.

        The method first verifies that the target account belongs to the
        requesting user (if ``account_id`` is provided).  It then loads all
        :class:`~app.models.corporate_action.CorporateAction` records and all
        existing **open** trades for the user, handing both — together with the
        raw bytes — to the appropriate broker parser.

        When the parser supports :meth:`parse_raw`, the raw-data pipeline is
        used (persist raw → create logical → aggregate → persist trades).
        Otherwise, the legacy ``parse()`` path is used (aggregate inside parser
        → persist trades).

        Trades that have ``is_manually_edited = True`` are skipped during
        re-import (matched by ``broker_conid`` + ``opened_at``) unless
        ``overwrite_manually_edited`` is ``True``.

        All inserts/updates happen within the caller's transaction; the service
        does **not** commit — that responsibility belongs to the route handler.

        Args:
            content: Raw file bytes from the upload.
            filename: Original filename (used by the parser for format
                detection).
            broker: The broker type that identifies which parser to use.
            account_id: Optional UUID of the account to associate trades
                with.  When ``None`` trades are created without an account
                association.
            user_id: UUID of the authenticated user — used to verify
                account ownership when ``account_id`` is given.
            overwrite_manually_edited: When ``True``, trades that have been
                manually edited are no longer protected — they will be
                overwritten by the incoming import data.  Defaults to
                ``False``.

        Returns:
            An :class:`~app.schemas.imports.ImportResult` summarising the
            outcome of the import.

        Raises:
            AccountNotFoundError: If ``account_id`` is provided but the
                account does not exist or does not belong to ``user_id``.
        """
        # Verify the account belongs to the requesting user (only if provided).
        portfolio_base_currency: str | None = None
        account = None
        if account_id is not None:
            account = await self._account_repo.get_by_id(
                account_id,
                user_id,
                portfolio_id,
            )
            if account is None:
                raise AccountNotFoundError(f"Account {account_id} not found for user {user_id}.")

        portfolio = await self._portfolio_repo.get_by_id(portfolio_id, user_id)
        if portfolio is not None:
            portfolio_base_currency = portfolio.base_currency

        # Load corporate actions for this user so the parser/aggregator can apply
        # split adjustments at the correct chronological point.
        corporate_actions = await self._ca_repo.list_by_user(user_id)

        # Load all existing open lots for this user so the aggregator can match
        # incoming closing executions against them (cross-period import support).
        open_lots = await self._trade_repo.list_open_lots_by_user(
            user_id,
            portfolio_id,
        )
        open_lot_ids = {lot.id for lot in open_lots}
        has_open_combo_seed_positions = False
        open_combo_positions: list[Trade] = []

        # Load all existing orphaned lots (closed, but no entry leg).
        orphaned_lots = await self._trade_repo.list_orphaned_lots_by_user(
            user_id,
            portfolio_id,
        )
        orphaned_lot_ids = {lot.id for lot in orphaned_lots}

        # Load the set of (broker_conid, opened_at) keys for manually-edited trades.
        manually_edited_keys = (
            await self._trade_repo.list_manually_edited_keys(
                user_id,
                portfolio_id,
            )
            if not overwrite_manually_edited
            else set()
        )

        # Load existing execution keys for deduplication to ensure idempotency.
        existing_entry_keys = await self._trade_repo.list_existing_entry_keys(
            user_id,
            account_id,
            portfolio_id,
        )
        existing_close_keys = await self._trade_repo.list_existing_close_keys(
            user_id,
            account_id,
            portfolio_id,
        )

        parser: BrokerParser = get_parser(broker)

        if broker == BrokerType.SCHWAB and account is not None:
            payload = self._decode_schwab_payload(content)
            accounts = payload.get("accounts")
            assert isinstance(accounts, list)
            if accounts:
                selected_account, selected_account_number = self._select_schwab_account_entry(
                    payload,
                    account_number=account.account_number,
                )
                if account.account_number is None and selected_account_number is not None:
                    account.account_number = selected_account_number
                    self._session.add(account)
                    await self._session.flush()
                    self._emit_account_number_bound_audit(
                        user_id=user_id,
                        account_id=account.id,
                        portfolio_id=portfolio_id,
                    )
                payload["accounts"] = [selected_account]
            content = json.dumps(payload).encode("utf-8")

        ca_for_parser: Sequence[CorporateActionLike] | None = cast(Sequence[CorporateActionLike], corporate_actions) if corporate_actions else None
        seed_for_parser: Sequence[SeedLotLike] | None = cast(Sequence[SeedLotLike], open_lots) if open_lots else None

        parser_warnings: list[str] = []
        suppressed_count: int = 0
        raw_records: list[BrokerRawTransactionCreate] = []
        parsed_corporate_actions: list[CorporateActionCreateRequest] = []
        inserted_raw_ids: set[str] = set()
        trades_with_sources: list[TradeCreateWithSources] = []

        # ── Raw-data pipeline (preferred) ────────────────────────────────────
        # Use parse_raw() when the parser supports it.  This persists each
        # execution as a BrokerRawTransaction and creates a 1:1 LogicalExecution
        # before running FIFO aggregation.
        try:
            raw_parse_result = parser.parse_raw(content, filename)
        except NotImplementedError:
            use_raw_pipeline = False
        else:
            if (
                isinstance(raw_parse_result, tuple)
                and len(raw_parse_result) == 2
                and isinstance(raw_parse_result[0], list)
                and isinstance(raw_parse_result[1], list)
            ):
                raw_records, parsed_corporate_actions = raw_parse_result
                use_raw_pipeline = True
            else:
                use_raw_pipeline = False

        if use_raw_pipeline:
            if account_id is not None:
                open_combo_positions = await self._trade_repo.list_open_combo_positions_by_user(
                    user_id=user_id,
                    portfolio_id=portfolio_id,
                    account_id=account_id,
                )
                has_open_combo_seed_positions = bool(open_combo_positions)

            for ca in parsed_corporate_actions:
                existing = await self._ca_repo.find_by_user_symbol_date_ratio(
                    user_id=user_id,
                    symbol=ca.symbol,
                    action_date=ca.date,
                    ratio=ca.ratio,
                )
                if existing is None:
                    await self._ca_repo.create(ca.to_corporate_action_create(user_id))

            # Reload corporate actions after adding new ones from the file
            corporate_actions = await self._ca_repo.list_by_user(user_id)
            ca_for_parser = cast(Sequence[CorporateActionLike], corporate_actions) if corporate_actions else None

            # Stamp user_id / account_id onto each raw record.
            stamped_raw: list[BrokerRawTransactionCreate] = []
            for rec in raw_records:
                # Prepend user_id to ensure the execution ID is globally unique
                # across all users (idempotent per user).
                new_id = rec.id if rec.id.startswith(f"{user_id}:") else f"{user_id}:{rec.id}"
                stamped_raw.append(
                    rec.model_copy(
                        update={
                            "id": new_id,
                            "user_id": user_id,
                            "account_id": account_id,
                        }
                    )
                )

            # Upsert raw records — already-existing rows are silently skipped.
            inserted_raw_ids = set(await self._raw_repo.bulk_upsert(stamped_raw))

            # For each newly inserted raw record, fetch the ORM object and create
            # a 1:1 LogicalExecution.
            newly_inserted_raw = [r for r in stamped_raw if r.id in inserted_raw_ids]
            new_orm_raws = []
            for rec in newly_inserted_raw:
                orm_raw = await self._raw_repo.get_by_id(rec.id)
                if orm_raw is not None:
                    new_orm_raws.append(orm_raw)

            _, suppressed_count = await self._logical_svc.bulk_create_from_raw(new_orm_raws)
            await self._session.flush()

            # Purge split-child executions and restore their soft-deleted parents
            # before re-aggregation.
            #
            # During backfill, an ``imported`` execution that maps to N>1 trades
            # is soft-deleted (deleted=True) and replaced by N ``split`` children.
            # On a subsequent import those split children must be removed and the
            # original ``imported`` parents restored so the FIFO pass operates on
            # the complete, non-duplicated base-execution layer.
            if account_id is not None:
                deleted_split = await self._exec_repo.delete_split_children_for_account(
                    user_id=user_id,
                    account_id=account_id,
                    override=overwrite_manually_edited,
                )
                if deleted_split:
                    restored_parents = await self._exec_repo.restore_split_parents_for_account(
                        user_id=user_id,
                        account_id=account_id,
                        override=overwrite_manually_edited,
                    )
                    logger.debug(
                        "import_split_cleanup account=%s deleted_split=%d restored_parents=%d",
                        account_id,
                        deleted_split,
                        restored_parents,
                    )
                await self._session.flush()

            # Rebuild the trade projection from scratch on every raw-pipeline
            # import, EXCEPT for trades backing still-open combo positions
            # (these are carried forward as seeds — see
            # _build_seed_combo_execution_trades — and must not be deleted out
            # from under themselves). Scoping the exclusion to just those
            # specific trades (rather than skipping the rebuild for the whole
            # account whenever ANY combo is open) prevents fragmented/split
            # single-instrument trades elsewhere in the account from being
            # duplicated on every subsequent import.
            #
            # This MUST run before `_collect_trade_creates_from_logical_batches`
            # below, which reads each execution's *current* `trade_id` into
            # `db_trade_id` — deleting trades afterwards would leave those
            # in-memory `db_trade_id` values pointing at rows that no longer
            # exist, causing the trade-creation loop to skip re-creating them
            # entirely (it treats "db_trade_id is not None" as "already
            # exists", regardless of whether that trade was just deleted).
            if account_id is not None:
                preserved_trade_ids = [trade.id for trade in open_combo_positions]
                await self._trade_repo.delete_by_user_account(
                    user_id=user_id,
                    account_id=account_id,
                    include_manually_edited=overwrite_manually_edited,
                    exclude_trade_ids=preserved_trade_ids,
                )
                await self._session.flush()

            # Load logical executions in batches to cap peak memory during import.
            parsed_trades = await self._collect_trade_creates_from_logical_batches(
                user_id=user_id,
                account_id=account_id,
                include_existing_trade_ids=has_open_combo_seed_positions,
            )

            # Run FIFO aggregation from the logical layer only.
            # Do not seed with existing trades in DB; for raw-pipeline imports we
            # rebuild the trade projection from logical executions.
            # Partition combo-eligible executions before FIFO so combo legs are not
            # collapsed into single-instrument round-trips.
            seed_combo_trades = await self._build_seed_combo_execution_trades(
                user_id=user_id,
                portfolio_id=portfolio_id,
                account_id=account_id,
                existing_source_ids={row.source_execution_id for row in parsed_trades if row.source_execution_id is not None},
            )
            combo_build_result = build_combo_positions([*seed_combo_trades, *parsed_trades])
            # Use the enhanced aggregation to track source executions
            # for split-aware linking.
            fifo_trades_with_sources = aggregate_executions_fifo_with_sources(
                combo_build_result.fifo_executions,
                corporate_actions=ca_for_parser,
                seed_open_lots=None,
                seed_orphaned_lots=None,
            )
            trades_with_sources = sorted(
                [*combo_build_result.combo_trades, *fifo_trades_with_sources],
                key=lambda tws: tws.trade_create.opened_at,
            )
            parser_warnings += combo_build_result.warnings

            # Extract plain TradeCreate objects for the existing trade processing logic
            parsed_trades = [tws.trade_create for tws in trades_with_sources]

        else:
            # ── Legacy pipeline (fallback) ────────────────────────────────────
            parsed_trades, _ = parser.parse(
                content,
                filename,
                corporate_actions=ca_for_parser,
                seed_open_lots=seed_for_parser,
                seed_orphaned_lots=cast(Sequence[SeedLotLike], orphaned_lots) if orphaned_lots else None,
            )

        # Enrich pnl_eur — base class provides a no-op default so this is always safe.
        await parser.enrich_pnl_eur(parsed_trades, self._session)

        # Collect parser warnings (IBKRXMLParser / SchwabParser expose .warnings).
        parser_warnings += getattr(parser, "warnings", [])

        trades_created = 0
        trades_updated = 0
        trades_skipped_manually_edited = 0
        create_warnings: list[str] = []
        raw_projection_rebuild = use_raw_pipeline and account_id is not None

        # Track db_trade_ids that have already been updated once.  If the same
        # seed lot appears more than once in parsed_trades (partial close split),
        # the first occurrence issues an UPDATE; subsequent occurrences become
        # INSERTs (new rows for the partial-close slices).
        already_updated_ids: set[uuid.UUID] = set()

        # For raw pipeline with source tracking, store created trades for backfilling
        if raw_projection_rebuild and use_raw_pipeline:
            for i, trade_data in enumerate(parsed_trades):
                match_key = (trade_data.broker_conid, trade_data.opened_at)
                if match_key in manually_edited_keys:
                    trades_skipped_manually_edited += 1
                    continue

                db_trade_id = trade_data.db_trade_id
                if db_trade_id is not None:
                    if db_trade_id in open_lot_ids or db_trade_id in orphaned_lot_ids:
                        is_orphan = db_trade_id in orphaned_lot_ids
                        is_ready_to_close = trade_data.closed_at is not None and (
                            trade_data.is_combo or (trade_data.exit_price is not None and trade_data.entry_price != Decimal("0.001"))
                        )
                        if is_ready_to_close and db_trade_id not in already_updated_ids:
                            try:
                                if is_orphan:
                                    await self._trade_repo.fill_orphaned_lot(
                                        trade_id=db_trade_id,
                                        user_id=user_id,
                                        entry_price=cast(Decimal, trade_data.entry_price),
                                        opened_at=trade_data.opened_at,
                                        pnl=trade_data.pnl,
                                        pnl_eur=trade_data.pnl_eur,
                                        net_pnl=trade_data.net_pnl,
                                        net_pnl_eur=trade_data.net_pnl_eur,
                                        commission_add=trade_data.commission,
                                        quantity=cast(Decimal, trade_data.quantity),
                                    )
                                elif trade_data.is_combo:
                                    await self._trade_repo.close_open_combo_trade(
                                        trade_id=db_trade_id,
                                        user_id=user_id,
                                        closed_at=cast(datetime, trade_data.closed_at),
                                        pnl=trade_data.pnl,
                                        pnl_eur=trade_data.pnl_eur,
                                        net_pnl=trade_data.net_pnl,
                                        net_pnl_eur=trade_data.net_pnl_eur,
                                        commission_total=trade_data.commission,
                                    )
                                else:
                                    await self._trade_repo.close_open_lot(
                                        trade_id=db_trade_id,
                                        user_id=user_id,
                                        exit_price=cast(Decimal, trade_data.exit_price),
                                        closed_at=cast(datetime, trade_data.closed_at),
                                        pnl=trade_data.pnl,
                                        pnl_eur=trade_data.pnl_eur,
                                        net_pnl=trade_data.net_pnl,
                                        net_pnl_eur=trade_data.net_pnl_eur,
                                        commission_add=trade_data.commission,
                                        quantity=cast(Decimal, trade_data.quantity),
                                    )
                                already_updated_ids.add(db_trade_id)
                                trades_updated += 1
                            except Exception as exc:  # noqa: BLE001
                                msg = f"Failed to update combo/seed trade {db_trade_id} ({trade_data.symbol}): {exc}"
                                logger.warning(msg)
                                create_warnings.append(msg)

                    existing_trade = await self._trade_repo.get_by_id(db_trade_id, user_id)
                    if existing_trade is not None and i < len(trades_with_sources):
                        trades_with_sources[i].created_trade = existing_trade
                    continue

                trade_with_owner = trade_data.model_copy(
                    update={
                        "account_id": account_id,
                        "user_id": user_id,
                        "db_trade_id": None,
                    }
                )
                try:
                    created_trade = await self._trade_repo.create(trade_with_owner)
                    # Store the created trade in the TradeCreateWithSources object
                    if i < len(trades_with_sources):
                        trades_with_sources[i].created_trade = created_trade
                    trades_created += 1
                except Exception as exc:  # noqa: BLE001
                    msg = f"Failed to persist trade {trade_data.symbol} opened at {trade_data.opened_at}: {exc}"
                    logger.warning(msg)
                    create_warnings.append(msg)

            # Backfill trade_id in logical executions using split-aware linking
            if use_raw_pipeline:
                await self._backfill_execution_trade_links(trades_with_sources, user_id)
                await self._assign_position_ids_from_sources(
                    trades_with_sources=trades_with_sources,
                    user_id=user_id,
                )
                # Execution-overwrite-protection: authoritative recompute of the
                # unlinked-duplicate conflict flag for every rebuilt trade.
                # Always set (never merged) so a cleared duplicate flips the
                # flag back to false on the same import.
                for tws in trades_with_sources:
                    trade = tws.created_trade
                    if trade is None:
                        continue
                    legs = await self._exec_repo.list_by_trade_id(trade.id, include_deleted=False)
                    trade.has_conflict = detect_duplicate_pairs(legs)
                await self._session.flush()

        for trade_data in parsed_trades:
            if raw_projection_rebuild and use_raw_pipeline:
                # Already processed above in the source-tracking path
                continue
            elif raw_projection_rebuild:
                match_key = (trade_data.broker_conid, trade_data.opened_at)
                if match_key in manually_edited_keys:
                    trades_skipped_manually_edited += 1
                    continue

                trade_with_owner = trade_data.model_copy(
                    update={
                        "account_id": account_id,
                        "user_id": user_id,
                        "db_trade_id": None,
                    }
                )
                try:
                    await self._trade_repo.create(trade_with_owner)
                    trades_created += 1
                except Exception as exc:  # noqa: BLE001
                    msg = f"Failed to persist trade {trade_data.symbol} opened at {trade_data.opened_at}: {exc}"
                    logger.warning(msg)
                    create_warnings.append(msg)
                continue

            db_trade_id = trade_data.db_trade_id

            # --- Case 1: This result closes an existing open DB lot (UPDATE) ---

            if db_trade_id is not None and (db_trade_id in open_lot_ids or db_trade_id in orphaned_lot_ids):
                is_orphan = db_trade_id in orphaned_lot_ids
                # Check for manual-edit protection on the original open lot
                match_key = (trade_data.broker_conid, trade_data.opened_at)
                if match_key in manually_edited_keys:
                    logger.debug(
                        "Skipping close of manually-edited trade: symbol=%s opened_at=%s",
                        trade_data.symbol,
                        trade_data.opened_at,
                    )
                    trades_skipped_manually_edited += 1
                    continue

                # Only update/insert if the trade is actually closed now
                if trade_data.closed_at is not None and trade_data.exit_price is not None and trade_data.entry_price != Decimal("0.001"):
                    if db_trade_id not in already_updated_ids:
                        # First close of this seed lot — UPDATE the original row.
                        try:
                            if is_orphan:
                                await self._trade_repo.fill_orphaned_lot(
                                    trade_id=db_trade_id,
                                    user_id=user_id,
                                    entry_price=cast(Decimal, trade_data.entry_price),
                                    opened_at=trade_data.opened_at,
                                    pnl=trade_data.pnl,
                                    pnl_eur=trade_data.pnl_eur,
                                    net_pnl=trade_data.net_pnl,
                                    net_pnl_eur=trade_data.net_pnl_eur,
                                    commission_add=trade_data.commission,
                                    quantity=cast(Decimal, trade_data.quantity),
                                )
                                # Create entry execution for newly filled orphaned lot
                                await self._exec_repo.create(
                                    user_id=user_id,
                                    account_id=account_id,
                                    symbol=trade_data.symbol,
                                    asset_class=trade_data.asset_class,
                                    direction=trade_data.direction,
                                    quantity=cast(Decimal, trade_data.quantity),
                                    price=cast(Decimal, trade_data.entry_price),
                                    commission=Decimal("0"),
                                    executed_at=trade_data.opened_at,
                                    multiplier=trade_data.multiplier or 1,
                                    currency=trade_data.currency,
                                    origin=EXECUTION_ORIGIN_IMPORTED,
                                    trade_id=db_trade_id,
                                )
                            else:
                                await self._trade_repo.close_open_lot(
                                    trade_id=db_trade_id,
                                    user_id=user_id,
                                    exit_price=trade_data.exit_price,
                                    closed_at=trade_data.closed_at,
                                    pnl=trade_data.pnl,
                                    pnl_eur=trade_data.pnl_eur,
                                    net_pnl=trade_data.net_pnl,
                                    net_pnl_eur=trade_data.net_pnl_eur,
                                    commission_add=trade_data.commission,
                                    quantity=cast(Decimal, trade_data.quantity),
                                )

                            # Create exit execution for closed lot
                            exit_direction = TradeDirection.SHORT if trade_data.direction == TradeDirection.LONG else TradeDirection.LONG
                            await self._exec_repo.create(
                                user_id=user_id,
                                account_id=account_id,
                                symbol=trade_data.symbol,
                                asset_class=trade_data.asset_class,
                                direction=exit_direction,
                                quantity=trade_data.quantity,
                                price=trade_data.exit_price,
                                commission=trade_data.commission,
                                executed_at=trade_data.closed_at,
                                multiplier=trade_data.multiplier or 1,
                                currency=trade_data.currency,
                                origin=EXECUTION_ORIGIN_IMPORTED,
                                trade_id=db_trade_id,
                                pnl=trade_data.pnl,
                            )

                            already_updated_ids.add(db_trade_id)
                            trades_updated += 1
                        except Exception as exc:  # noqa: BLE001
                            msg = f"Failed to close/fill open/orphaned lot {db_trade_id} ({trade_data.symbol}): {exc}"
                            logger.warning(msg)
                            create_warnings.append(msg)
                    else:
                        # Subsequent partial close of same seed lot — INSERT a
                        # new row so the full close history is preserved.
                        trade_with_owner = trade_data.model_copy(update={"account_id": account_id, "user_id": user_id})
                        try:
                            await self._trade_repo.create(trade_with_owner)
                            trades_created += 1
                        except Exception as exc:  # noqa: BLE001
                            msg = f"Failed to insert partial close for {trade_data.symbol} closed at {trade_data.closed_at}: {exc}"
                            logger.warning(msg)
                            create_warnings.append(msg)
                else:
                    # If still open (or still orphaned), check if the original
                    # seed lot was already updated.
                    if db_trade_id in already_updated_ids:
                        # The original seed row was partially matched and updated
                        # to represent the matched portion.
                        # This remaining unmatched portion must be inserted as a
                        # new row to avoid losing it.
                        trade_with_owner = trade_data.model_copy(
                            update={
                                "account_id": account_id,
                                "user_id": user_id,
                                "id": None,
                            }
                        )
                        try:
                            await self._trade_repo.create(trade_with_owner)
                            trades_created += 1
                        except Exception as exc:  # noqa: BLE001
                            msg = f"Failed to insert remaining open/orphaned lot for {trade_data.symbol}: {exc}"
                            logger.warning(msg)
                            create_warnings.append(msg)
                    # If not in already_updated_ids, it means the seed lot wasn't
                    # touched. Skip (already in DB).
                continue

            # --- Case 2: Seed lot that is still open — skip (already in DB) ---
            if db_trade_id is not None and db_trade_id not in open_lot_ids and db_trade_id not in orphaned_lot_ids:
                # db_trade_id set but not in open_lot_ids — shouldn't happen, skip
                logger.debug("Skipping seed lot with unknown db_trade_id=%s", db_trade_id)
                continue

            # --- Case 3: Seed lot that stayed open (no db_trade_id, but it is
            #             a duplicate of an existing open lot) — detected via
            #             the open lot still being open after aggregation.
            # NOTE: Seed lots that remain open come back from the aggregator with
            # db_trade_id set (they were created from seeds).  If db_trade_id is
            # None and closed_at is None, it is a genuinely new open position from
            # this file.

            # --- Case 4: Entirely new trade (INSERT) ---
            # Skip trades that the user has manually corrected (task 5.2).
            match_key = (trade_data.broker_conid, trade_data.opened_at)
            if match_key in manually_edited_keys:
                logger.debug(
                    "Skipping re-import of manually-edited trade: symbol=%s opened_at=%s",
                    trade_data.symbol,
                    trade_data.opened_at,
                )
                trades_skipped_manually_edited += 1
                continue

            # Deduplication: check against existing execution keys.
            is_orphan = trade_data.entry_price == Decimal("0.001")

            # 1. Match entry leg for regular (non-orphaned) trades.
            if not is_orphan:
                entry_key = (
                    trade_data.symbol,
                    trade_data.opened_at,
                    trade_data.entry_price,
                    trade_data.quantity,
                    trade_data.direction.value,
                )
                if entry_key in existing_entry_keys:
                    logger.debug(
                        "Skipping duplicate entry trade: symbol=%s opened_at=%s",
                        trade_data.symbol,
                        trade_data.opened_at,
                    )
                    continue

            # 2. Match closing leg (either it's an orphaned close,
            # or a full open/close trade).
            close_key: tuple[str, datetime, Decimal, Decimal, str] | None = None
            trade_data_symbol = trade_data.symbol
            trade_data_opened_at = trade_data.opened_at
            trade_data_exit_price = trade_data.exit_price
            trade_data_quantity = trade_data.quantity
            trade_data_direction_val = trade_data.direction.value
            if is_orphan:
                # For orphaned trades, the 'opened_at' is actually the
                # execution time of the close leg.
                if trade_data_exit_price is not None and trade_data_quantity is not None:
                    close_key = (
                        trade_data_symbol,
                        trade_data_opened_at,
                        trade_data_exit_price,
                        trade_data_quantity,
                        trade_data_direction_val,
                    )
            else:
                # For regular trades that are closed, closed_at is the
                # execution time of the close leg.
                trade_data_closed_at = trade_data.closed_at
                if trade_data_closed_at and trade_data_exit_price is not None and trade_data_quantity is not None:
                    close_key = (
                        trade_data_symbol,
                        trade_data_closed_at,
                        trade_data_exit_price,
                        trade_data_quantity,
                        trade_data_direction_val,
                    )

            if close_key is not None and close_key in existing_close_keys:
                logger.debug(
                    "Skipping duplicate close execution: symbol=%s close_time=%s",
                    trade_data.symbol,
                    close_key[1],
                )
                continue

            # Stamp both account_id and user_id onto each trade before persisting.
            trade_with_owner = trade_data.model_copy(update={"account_id": account_id, "user_id": user_id})
            try:
                created_trade = await self._trade_repo.create(trade_with_owner)
                trades_created += 1
                # ── Synthetic execution legs for legacy-imported trades ────────
                # The legacy pipeline does not create LogicalExecution rows,
                # so we synthesise them here so the Execution Legs table is
                # populated for every imported trade.
                exit_direction = TradeDirection.SHORT if trade_data.direction == TradeDirection.LONG else TradeDirection.LONG
                await self._exec_repo.create(
                    user_id=user_id,
                    account_id=account_id,
                    symbol=created_trade.symbol,
                    asset_class=created_trade.asset_class,
                    direction=created_trade.direction,
                    quantity=created_trade.quantity,
                    price=created_trade.entry_price,
                    commission=created_trade.commission,
                    executed_at=created_trade.opened_at,
                    multiplier=created_trade.multiplier,
                    currency=created_trade.currency,
                    origin=EXECUTION_ORIGIN_IMPORTED,
                    trade_id=created_trade.id,
                )
                if created_trade.closed_at is not None and created_trade.exit_price is not None:
                    await self._exec_repo.create(
                        user_id=user_id,
                        account_id=account_id,
                        symbol=created_trade.symbol,
                        asset_class=created_trade.asset_class,
                        direction=exit_direction,
                        quantity=created_trade.quantity,
                        price=created_trade.exit_price,
                        commission=created_trade.commission,
                        executed_at=created_trade.closed_at,
                        multiplier=created_trade.multiplier,
                        currency=created_trade.currency,
                        origin=EXECUTION_ORIGIN_IMPORTED,
                        trade_id=created_trade.id,
                        pnl=created_trade.pnl,
                    )
            except Exception as exc:  # noqa: BLE001
                msg = f"Failed to persist trade {trade_data.symbol} opened at {trade_data.opened_at}: {exc}"
                logger.warning(msg)
                create_warnings.append(msg)

        all_warnings: list[str] = parser_warnings + create_warnings

        if portfolio_base_currency is not None:
            mismatched_count = sum(1 for trade_data in parsed_trades if trade_data.currency is not None and trade_data.currency != portfolio_base_currency)
            if mismatched_count > 0:
                all_warnings.append(
                    "currency_mismatch: "
                    f"{mismatched_count} imported trade(s) use a currency "
                    "different from portfolio "
                    f"base_currency '{portfolio_base_currency}'."
                )

        # Trades parsed = all aggregated trades minus seed-only open lots
        # (seed lots that stayed open are returned by the aggregator but have
        # db_trade_id set; they are not "parsed" from this file).
        new_trades_parsed = sum(1 for t in parsed_trades if t.db_trade_id is None)
        # Skipped = new trades (no db_trade_id) that failed to insert.
        # trades_created may be higher than new_trades_parsed when partial-close
        # splits generate extra INSERT rows — clamp to 0 to avoid a negative value.
        trades_skipped = max(
            0,
            new_trades_parsed - trades_created - trades_skipped_manually_edited,
        )

        return ImportResult(
            broker=str(broker),
            filename=filename,
            trades_parsed=new_trades_parsed,
            trades_created=trades_created,
            trades_skipped=trades_skipped,
            raw_transactions_created=len(inserted_raw_ids) if use_raw_pipeline else 0,
            raw_suppressed_skipped=suppressed_count,
            raw_deleted_skipped=0,
            warnings=all_warnings,
        )

    async def fresh_start_import(
        self,
        content: bytes,
        filename: str,
        broker: BrokerType,
        portfolio_id: uuid.UUID,
        account_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> FreshStartResult:
        """Reset an account and re-import from scratch (Decision 6).

        Runs in a single DB transaction (managed by the caller/session dependency):
        1. Delete all ``LogicalExecution`` rows for the account (hard-delete ALL).
        2. Delete all ``Trade`` rows for the account.
        3. Process the uploaded import file normally.
        4. Commit — or roll back entirely on any error.

        BRTs are never touched — only their linked logical executions are removed.
        Suppressed BRTs remain suppressed and will still be skipped during the
        re-import.

        Args:
            content: Raw file bytes from the upload.
            filename: Original filename (used by the parser for format detection).
            broker: The broker type that identifies which parser to use.
            account_id: UUID of the account to reset and re-import.
            user_id: UUID of the authenticated user — used to verify account
                ownership.

        Returns:
            A :class:`FreshStartResult` with counts of deleted rows and the
            import result.

        Raises:
            AccountNotFoundError: If the account does not exist or does not
                belong to ``user_id``.
        """
        account = await self._account_repo.get_by_id(account_id, user_id, portfolio_id)
        if account is None:
            raise AccountNotFoundError(f"Account {account_id} not found for user {user_id}.")

        # Step 1: Delete all logical executions for this account
        exec_deleted = await self._exec_repo.delete_all_for_account(
            user_id=user_id,
            account_id=account_id,
        )

        # Step 1.5: Delete all raw transactions for this account so that
        # re-import can recreate logical executions from raw records.
        raw_deleted = await self._raw_repo.delete_by_user_account(
            user_id=user_id,
            account_id=account_id,
        )

        # Step 2: Delete all trades for this account (including manually-edited)
        trades_deleted = await self._trade_repo.delete_by_user_account(
            user_id=user_id,
            account_id=account_id,
            include_manually_edited=True,
        )

        logger.info(
            "fresh_start_import: deleted %d raw transactions, %d executions and %d trades for account %s",
            raw_deleted,
            exec_deleted,
            trades_deleted,
            account_id,
        )

        # Step 3: Process the import file
        import_result = await self.import_file(
            content=content,
            filename=filename,
            broker=broker,
            portfolio_id=portfolio_id,
            account_id=account_id,
            user_id=user_id,
            overwrite_manually_edited=True,
        )

        return FreshStartResult(
            account_id=account_id,
            executions_deleted=exec_deleted,
            trades_deleted=trades_deleted,
            import_result=import_result,
        )

    async def suppress_raw_transaction(
        self,
        raw_id: str,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID | None = None,
        suppressed: bool = True,
    ) -> None:
        """Toggle the suppressed flag on a BrokerRawTransaction.

        Args:
            raw_id: The composite ID of the raw transaction.
            user_id: The authenticated user's ID (for ownership check).
            suppressed: New value for the suppressed flag.

        Raises:
            AccountNotFoundError: If the raw transaction is not found or
                does not belong to ``user_id``.
        """
        raw = await self._raw_repo.get_by_id(raw_id)
        if raw is None or raw.user_id != user_id:
            from app.core.exceptions import BrokerRawTransactionNotFoundError

            raise BrokerRawTransactionNotFoundError(f"BrokerRawTransaction {raw_id} not found.")
        if raw.account_id is not None and portfolio_id is not None:
            account = await self._account_repo.get_by_id(
                raw.account_id,
                user_id,
                portfolio_id,
            )
            if account is None:
                from app.core.exceptions import BrokerRawTransactionNotFoundError

                raise BrokerRawTransactionNotFoundError(f"BrokerRawTransaction {raw_id} not found.")
        if portfolio_id is not None:
            portfolio = await self._portfolio_repo.get_by_id(portfolio_id, user_id)
            if portfolio is None:
                from app.core.exceptions import BrokerRawTransactionNotFoundError

                raise BrokerRawTransactionNotFoundError(f"BrokerRawTransaction {raw_id} not found.")
        await self._raw_repo.set_suppressed(raw_id, suppressed)

    async def _backfill_execution_trade_links(
        self,
        trades_with_sources: list[TradeCreateWithSources],
        user_id: uuid.UUID,
    ) -> None:
        """Backfill execution ``trade_id`` links with split-aware validation.

        The method builds an execution usage map from aggregated trades, validates
        ownership and quantity/commission constraints, then applies links using a
        bulk path for direct assignments and savepoint-protected split operations
        for multi-trade executions.

        Args:
            trades_with_sources: Aggregated trades with source allocation metadata.
            user_id: Authenticated user ID.

        Raises:
            TradeNotFoundError: If a referenced trade does not exist for the user.
            ExecutionNotFoundError: If a referenced execution does not exist.
            ExecutionValidationError: If quantity/commission or consistency checks fail.
        """
        if not trades_with_sources:
            return

        started_at = perf_counter()
        query_count = 0
        memory_peak_bytes = 0

        bind = None
        if isinstance(self._session, AsyncSession):
            bind = self._session.get_bind()
        sync_engine = getattr(bind, "sync_engine", None)

        def _before_cursor_execute(
            conn: object,
            cursor: object,
            statement: object,
            parameters: object,
            context: object,
            executemany: object,
        ) -> None:
            del conn, cursor, statement, parameters, context, executemany
            nonlocal query_count
            query_count += 1

        query_listener_installed = False
        if sync_engine is not None and hasattr(sync_engine, "dispatch"):
            event.listen(sync_engine, "before_cursor_execute", _before_cursor_execute)
            query_listener_installed = True
        tracemalloc_started = False
        if not tracemalloc.is_tracing():
            tracemalloc.start()
            tracemalloc_started = True
        processed_trade_ids: set[uuid.UUID] = set()
        execution_usage_map: dict[uuid.UUID | str, list[tuple[uuid.UUID, ExecutionAllocation]]] = {}

        try:
            for trade_source in trades_with_sources:
                trade = trade_source.created_trade
                if trade is None:
                    continue
                processed_trade_ids.add(trade.id)

                for allocation in trade_source.source_executions:
                    execution_usage_map.setdefault(allocation.execution_id, []).append((trade.id, allocation))

            for trade_id in processed_trade_ids:
                db_trade = await self._trade_repo.get_by_id(trade_id, user_id)
                if db_trade is None:
                    raise TradeNotFoundError(f"Trade {trade_id} not found for split-aware backfill.")

            direct_pairs: list[tuple[uuid.UUID, uuid.UUID]] = []
            split_inputs: dict[
                uuid.UUID,
                tuple[LogicalExecution, list[tuple[uuid.UUID, ExecutionAllocation]]],
            ] = {}

            execution_ids = list(execution_usage_map.keys())
            if execution_ids:
                # Filter out string IDs (ground-truth) from DB backfill check.
                # Ground-truth executions are already validated during aggregation.
                db_execution_ids = [eid for eid in execution_ids if isinstance(eid, uuid.UUID)]
                fetched_executions = await self._list_executions_for_backfill(
                    execution_ids=db_execution_ids,
                    user_id=user_id,
                )
                execution_by_id = {execution.id: execution for execution in fetched_executions}

                # Build a mapping of trade_id to its TradeCreate object for easy lookup
                trade_create_map: dict[uuid.UUID, TradeCreate] = {}
                for trade_source in trades_with_sources:
                    trade = trade_source.created_trade
                    if trade is None:
                        continue
                    trade_create_map[trade.id] = trade_source.trade_create

                for execution_id, usage_list in execution_usage_map.items():
                    # Skip non-UUID IDs (ground-truth sentinel IDs) from
                    # further DB-level backfill.
                    if not isinstance(execution_id, uuid.UUID):
                        continue

                    execution = execution_by_id.get(execution_id)
                    if execution is None:
                        raise ExecutionNotFoundError(f"Execution {execution_id} not found for split-aware backfill.")

                    # Recompute commission_used proportionally from the original
                    # execution's commission.
                    exec_qty = execution.quantity
                    exec_comm = execution.commission
                    corrected_usage_list: list[tuple[uuid.UUID, ExecutionAllocation]] = []

                    # Deduplicate allocations per trade: an execution can appear as
                    # both opening and closing leg of the same trade in position flips.
                    # Only the first occurrence per (execution, trade) pair is kept.
                    trade_allocation_map: dict[uuid.UUID, ExecutionAllocation] = {}

                    for trade_id, alloc in usage_list:
                        if trade_id in trade_allocation_map:
                            # Already seen this execution in this trade.
                            # Verify quantity matches (should be same for flip).
                            existing = trade_allocation_map[trade_id]
                            if existing.quantity_used != alloc.quantity_used:
                                logger.warning(
                                    "Execution %s mismatched qty for trade %s: %s != %s",
                                    execution_id,
                                    trade_id,
                                    existing.quantity_used,
                                    alloc.quantity_used,
                                )
                            continue

                        proportional_comm = exec_comm * alloc.quantity_used / exec_qty if exec_qty > Decimal("0") else Decimal("0")

                        corrected_alloc = ExecutionAllocation(
                            execution_id=alloc.execution_id,
                            quantity_used=alloc.quantity_used,
                            commission_used=proportional_comm,
                            entry_price=alloc.entry_price,
                        )
                        trade_allocation_map[trade_id] = corrected_alloc
                        corrected_usage_list.append((trade_id, corrected_alloc))

                    usage_list = corrected_usage_list
                    execution_usage_map[execution_id] = usage_list

                    allocations = [allocation for _, allocation in usage_list]
                    self._validate_split_quantities(execution.quantity, allocations)
                    self._validate_split_commissions(execution.commission, allocations)

                    if len(usage_list) == 1:
                        direct_pairs.append((execution_id, usage_list[0][0]))
                    else:
                        split_inputs[execution_id] = (execution, usage_list)

            direct_updated = 0
            if direct_pairs:
                async with self._session.begin_nested():
                    direct_updated = await self._exec_repo.bulk_update_trade_ids(direct_pairs)

            split_children_created = 0
            split_errors = 0
            for execution_id, (execution, usage_list) in split_inputs.items():
                operation = self._split_operation_callable(
                    execution=execution,
                    usage_list=usage_list,
                    user_id=user_id,
                )
                try:
                    async with self._session.begin_nested():
                        split_children_created += await self._with_retry(
                            operation_name="process_execution_split",
                            operation=operation,
                        )
                except (ExecutionNotFoundError, ExecutionValidationError) as exc:
                    split_errors += 1
                    logger.error(
                        "split_backfill_failed execution_id=%s user_id=%s error=%s",
                        execution_id,
                        user_id,
                        str(exc),
                        exc_info=True,
                    )

            if split_inputs:
                await self._validate_split_backfill_consistency(split_inputs)

            orphaned_children = await self._find_orphaned_children_for_trades(
                trades_with_sources=trades_with_sources,
                user_id=user_id,
            )
            if orphaned_children > 0:
                orphaned_children = await self._resolve_orphaned_children_for_trades(
                    trades_with_sources=trades_with_sources,
                    user_id=user_id,
                )

            _, memory_peak_bytes = tracemalloc.get_traced_memory()
            elapsed_ms = (perf_counter() - started_at) * MILLISECONDS_PER_SECOND
            logger.info(
                "split_backfill_complete user_id=%s trades=%d executions=%d "
                "direct_updated=%d split_parents=%d split_children_created=%d "
                "split_errors=%d orphaned_children=%d query_count=%d "
                "memory_peak_bytes=%d duration_ms=%.2f",
                user_id,
                len(processed_trade_ids),
                len(execution_usage_map),
                direct_updated,
                len(split_inputs),
                split_children_created,
                split_errors,
                orphaned_children,
                query_count,
                memory_peak_bytes,
                elapsed_ms,
            )
            if memory_peak_bytes >= IMPORT_MEMORY_ALERT_THRESHOLD_BYTES:
                logger.warning(
                    "split_backfill_memory_threshold_exceeded user_id=%s peak_bytes=%d threshold_bytes=%d",
                    user_id,
                    memory_peak_bytes,
                    IMPORT_MEMORY_ALERT_THRESHOLD_BYTES,
                )
        finally:
            if query_listener_installed:
                event.remove(
                    sync_engine,
                    "before_cursor_execute",
                    _before_cursor_execute,
                )
            if tracemalloc_started:
                tracemalloc.stop()

    async def _assign_position_ids_from_sources(
        self,
        trades_with_sources: list[TradeCreateWithSources],
        user_id: uuid.UUID,
    ) -> None:
        """Assign shared position IDs for split-derived trade groups.

        Trades that originate from the same source execution are treated as one
        business position and receive a shared ``position_id``.

        Args:
            trades_with_sources: Created trades with source execution allocations.
            user_id: Owning user UUID.
        """
        execution_to_trade_ids: dict[uuid.UUID | str, set[uuid.UUID]] = {}
        trade_by_id: dict[uuid.UUID, object] = {}

        for trade_source in trades_with_sources:
            created_trade = trade_source.created_trade
            if created_trade is None:
                continue
            trade_by_id[created_trade.id] = created_trade
            for allocation in trade_source.source_executions:
                trade_ids = execution_to_trade_ids.setdefault(
                    allocation.execution_id,
                    set(),
                )
                trade_ids.add(created_trade.id)

        for trade_ids in execution_to_trade_ids.values():
            if len(trade_ids) < 2:
                continue

            canonical_position_id = None
            for trade_id in trade_ids:
                trade_obj = trade_by_id.get(trade_id)
                trade_position_id = getattr(trade_obj, "position_id", None)
                if trade_position_id is not None:
                    canonical_position_id = trade_position_id
                    break

            if canonical_position_id is None:
                canonical_position_id = uuid.uuid4()

            await self._trade_repo.update_position_id(
                trade_ids=list(trade_ids),
                position_id=canonical_position_id,
                user_id=user_id,
            )

    async def _list_executions_for_backfill(
        self,
        execution_ids: list[uuid.UUID],
        user_id: uuid.UUID,
    ) -> list[LogicalExecution]:
        """Load executions for backfill in bounded batches.

        Args:
            execution_ids: IDs referenced by split-aware allocation usage.
            user_id: Owning user UUID for ownership filtering.

        Returns:
            Execution rows for the provided IDs that belong to ``user_id``.
        """
        loaded: list[LogicalExecution] = []
        for execution_id_batch in self._exec_repo.iter_batches(
            execution_ids,
            batch_size=IMPORT_EXECUTIONS_BATCH_SIZE,
        ):
            batch_rows = await self._exec_repo.list_by_ids(execution_id_batch)
            loaded.extend(row for row in batch_rows if row.user_id == user_id)
        return loaded

    async def _collect_trade_creates_from_logical_batches(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID | None,
        include_existing_trade_ids: bool = False,
    ) -> list[TradeCreate]:
        """Collect converted TradeCreate rows from paged logical executions.

        Args:
            user_id: Owning user UUID.
            account_id: Optional account UUID filter.

        Returns:
            Converted trades in execution-time order.
        """
        collected: list[TradeCreate] = []
        async for trade_batch in self._iter_trade_creates_from_logical_batches(
            user_id=user_id,
            account_id=account_id,
            include_existing_trade_ids=include_existing_trade_ids,
        ):
            collected.extend(trade_batch)
        return collected

    async def _iter_trade_creates_from_logical_batches(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID | None,
        include_existing_trade_ids: bool = False,
    ) -> AsyncIterator[list[TradeCreate]]:
        """Yield converted TradeCreate rows in bounded batches.

        Args:
            user_id: Owning user UUID.
            account_id: Optional account UUID filter.

        Yields:
            Lists of converted :class:`TradeCreate` rows.
        """
        offset = 0
        while True:
            logical_batch = await self._logical_svc.list_by_user(
                user_id=user_id,
                account_id=account_id,
                limit=IMPORT_EXECUTIONS_BATCH_SIZE,
                offset=offset,
            )
            if not logical_batch:
                return
            trade_batch = logical_executions_to_trade_creates(cast(list[ExecutionLike], logical_batch))

            raw_ids = [row.source_id for row in logical_batch if row.source_id]
            combo_meta_by_raw_id = await self._raw_repo.get_combo_order_meta_by_raw_ids(raw_ids)

            for logical_row, trade_row in zip(logical_batch, trade_batch, strict=False):
                source_id = logical_row.source_id
                if source_id:
                    combo_meta = combo_meta_by_raw_id.get(source_id)
                    if combo_meta is not None:
                        trade_row.broker_order_id = cast(str | None, combo_meta.get("brokerageOrderID"))
                        trade_row.net_cash = cast(Decimal | None, combo_meta.get("netCash"))
                trade_row.open_close = logical_row.open_close
                if include_existing_trade_ids:
                    trade_row.db_trade_id = logical_row.trade_id

            yield trade_batch
            if len(logical_batch) < IMPORT_EXECUTIONS_BATCH_SIZE:
                return
            offset += IMPORT_EXECUTIONS_BATCH_SIZE

    async def _build_seed_combo_execution_trades(
        self,
        *,
        user_id: uuid.UUID,
        portfolio_id: uuid.UUID,
        account_id: uuid.UUID | None,
        existing_source_ids: set[uuid.UUID | str],
    ) -> list[TradeCreate]:
        """Build TradeCreate seed legs for open COMBO trades.

        These seed rows carry ``db_trade_id`` so a later close can update the
        existing open COMBO trade instead of inserting a duplicate.
        """
        open_combo_trades = await self._trade_repo.list_open_combo_positions_by_user(
            user_id=user_id,
            portfolio_id=portfolio_id,
            account_id=account_id,
        )

        opening_legs: list[LogicalExecution] = []
        leg_meta: dict[uuid.UUID, tuple[uuid.UUID, str | None]] = {}
        for trade in open_combo_trades:
            for leg in trade.logical_executions:
                if leg.deleted or leg.open_close != "O":
                    continue
                if leg.id in existing_source_ids:
                    continue
                opening_legs.append(leg)
                leg_meta[leg.id] = (trade.id, trade.broker_order_id)

        if not opening_legs:
            return []

        seed_rows = logical_executions_to_trade_creates(cast(list[ExecutionLike], opening_legs))
        for leg, row in zip(opening_legs, seed_rows, strict=False):
            db_trade_id, broker_order_id = leg_meta[leg.id]
            row.db_trade_id = db_trade_id
            row.broker_order_id = broker_order_id
            row.open_close = leg.open_close

        return seed_rows

    def _decode_schwab_payload(self, content: bytes) -> dict[str, object]:
        return decode_schwab_wrapped_payload(content)

    def _emit_account_number_bound_audit(
        self,
        *,
        user_id: uuid.UUID,
        account_id: uuid.UUID,
        portfolio_id: uuid.UUID,
    ) -> None:
        """Emit manual audit event when account_number is auto-bound during import."""
        self._audit.create_audit_event(
            action="account.account_number_bound",
            user_id=user_id,
            email=None,
            resource_type="account",
            resource_id=account_id,
            parent_resource_type="portfolio",
            parent_resource_id=portfolio_id,
            ip_address=None,
            user_agent=None,
            request_id=generate_request_id(),
            status_code=200,
            method="SYSTEM",
            path="import_service.import_file",
            metadata={
                "reason": "schwab_single_account_auto_bind",
            },
        )

    def _select_schwab_account_entry(
        self,
        payload: dict[str, object],
        account_number: str | None,
    ) -> tuple[dict[str, object], str | None]:
        accounts_obj = payload.get("accounts")
        assert isinstance(accounts_obj, list)
        file_accounts: list[dict[str, object]] = [entry for entry in accounts_obj if isinstance(entry, dict)]
        if len(file_accounts) != len(accounts_obj):
            raise ImportParseError("Schwab JSON payload contains invalid account entries; each accounts item must be an object.")

        return resolve_schwab_account_entry(
            accounts=file_accounts,
            configured_account_number=account_number,
            context="import",
        )

    @staticmethod
    @lru_cache(maxsize=16)
    def _retry_delays(max_attempts: int) -> tuple[float, ...]:
        """Return exponential retry delays for transient DB operations.

        Args:
            max_attempts: Maximum operation attempts.

        Returns:
            Tuple of delays (seconds) between attempts.
        """
        if max_attempts <= 1:
            return ()
        return tuple(IMPORT_RETRY_BASE_DELAY_SECONDS * (2**attempt) for attempt in range(max_attempts - 1))

    async def _with_retry(
        self,
        operation_name: str,
        operation: Callable[[], Awaitable[int]],
    ) -> int:
        """Run an async DB operation with transient-error retries.

        Args:
            operation_name: Name used in retry logs.
            operation: Zero-argument callable returning an awaitable operation.

        Returns:
            Result of the successful operation.

        Raises:
            OperationalError: When all retry attempts are exhausted.
            DBAPIError: When all retry attempts are exhausted.
        """
        delays = self._retry_delays(IMPORT_RETRY_MAX_ATTEMPTS)
        attempt = 1
        while True:
            try:
                return await operation()
            except (OperationalError, DBAPIError):
                if attempt >= IMPORT_RETRY_MAX_ATTEMPTS:
                    raise
                delay = delays[attempt - 1]
                logger.warning(
                    "import_retry operation=%s attempt=%d/%d delay=%.3fs",
                    operation_name,
                    attempt,
                    IMPORT_RETRY_MAX_ATTEMPTS,
                    delay,
                    exc_info=True,
                )
                await asyncio.sleep(delay)
                attempt += 1

    def _split_operation_callable(
        self,
        execution: LogicalExecution,
        usage_list: list[tuple[uuid.UUID, ExecutionAllocation]],
        user_id: uuid.UUID,
    ) -> Callable[[], Awaitable[int]]:
        """Create a bound callable for retrying split processing safely.

        Args:
            execution: Parent execution row to split.
            usage_list: Target allocations for the split children.
            user_id: Owning user UUID.

        Returns:
            Zero-arg async callable suitable for :meth:`_with_retry`.
        """

        async def _operation() -> int:
            return await self._process_execution_split(
                execution=execution,
                usage_list=usage_list,
                user_id=user_id,
            )

        return _operation

    async def _process_execution_split(
        self,
        execution: "LogicalExecution",
        usage_list: list[tuple[uuid.UUID, ExecutionAllocation]],
        user_id: uuid.UUID,
    ) -> int:
        """Process a multi-trade execution split.

        Creates split children for each trade that uses this execution,
        following the simplified-execution-model conventions.

        Args:
            execution: The execution ORM row to split.
            usage_list: List of (trade_id, allocation) pairs showing how this
                execution is divided across trades.
            user_id: User ID for validation.

        Returns:
            Number of child executions created.

        Raises:
            ExecutionNotFoundError: If soft-delete cannot locate the parent row.
            ExecutionValidationError: If validation fails before split.
        """
        execution_id = execution.id
        if execution.user_id != user_id:
            raise ExecutionValidationError(f"Execution {execution_id} does not belong to user {user_id}.")

        allocations = [allocation for _, allocation in usage_list]
        self._validate_split_quantities(execution.quantity, allocations)
        self._validate_split_commissions(execution.commission, allocations)

        parent_deleted = await self._exec_repo.soft_delete(execution_id)
        if not parent_deleted:
            raise ExecutionNotFoundError(f"Execution {execution_id} not found during split soft-delete.")

        created_children = 0
        for trade_id, allocation in usage_list:
            await self._exec_repo.create(
                user_id=execution.user_id,
                account_id=execution.account_id,
                symbol=execution.symbol,
                conid=execution.conid,
                asset_class=execution.asset_class,
                direction=execution.direction,
                quantity=allocation.quantity_used,
                price=execution.price,
                commission=allocation.commission_used,
                executed_at=execution.executed_at,
                pnl=execution.pnl if trade_id == usage_list[0][0] else None,
                currency=execution.currency,
                multiplier=execution.multiplier,
                origin=EXECUTION_ORIGIN_SPLIT,
                parent_id=execution.id,
                trade_id=trade_id,
                strike=execution.strike,
                expiry=execution.expiry,
                option_type=execution.option_type,
                open_close=execution.open_close,
            )
            created_children += 1

        logger.debug(
            "split_execution_created execution_id=%s children=%d quantities=%s",
            execution_id,
            len(usage_list),
            [allocation.quantity_used for _, allocation in usage_list],
        )

        return created_children

    async def _split_execution_for_trade(
        self,
        execution_id: uuid.UUID,
        quantity_for_trade: Decimal,
        trade_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> "LogicalExecution":
        """Split an execution using simplified-execution-model split logic.

        Following the simplified-execution-model conventions:
        1. Soft-delete the original execution (deleted=true)
        2. Create child execution for the specific trade with origin='split'
        3. Create remainder child for future allocation (if quantity remains)
        4. Set parent_id on both children to original execution ID

        Args:
            execution_id: ID of the original execution to split.
            quantity_for_trade: Portion allocated to the specified trade.
            trade_id: Target trade ID for the allocated portion.
            user_id: User ID for validation and record creation.

        Returns:
            The child execution assigned to the trade.

        Raises:
            ValueError: If quantity_for_trade exceeds original execution quantity.
        """
        db_trade = await self._trade_repo.get_by_id(trade_id, user_id)
        if db_trade is None:
            raise TradeNotFoundError(f"Trade {trade_id} not found for user {user_id}.")

        # 1. Load original execution
        original = await self._exec_repo.get_by_id(execution_id, user_id=user_id)
        if not original:
            raise ExecutionNotFoundError(f"Execution {execution_id} not found.")

        self._validate_split_quantities(
            original.quantity,
            [
                ExecutionAllocation(
                    execution_id=execution_id,
                    quantity_used=quantity_for_trade,
                    commission_used=Decimal("0"),
                    entry_price=original.price,
                )
            ],
        )

        # 2. Calculate proportional commission
        commission_for_trade = (original.commission * quantity_for_trade) / original.quantity if original.quantity > 0 else Decimal("0")

        self._validate_split_commissions(
            original.commission,
            [
                ExecutionAllocation(
                    execution_id=execution_id,
                    quantity_used=quantity_for_trade,
                    commission_used=commission_for_trade,
                    entry_price=original.price,
                )
            ],
        )

        # 3. Soft-delete original (preserves BRT link)
        await self._exec_repo.soft_delete(execution_id)

        # 4. Create child for this specific trade
        child_for_trade = await self._exec_repo.create(
            user_id=original.user_id,
            account_id=original.account_id,
            symbol=original.symbol,
            conid=original.conid,
            asset_class=original.asset_class,
            direction=original.direction,
            quantity=quantity_for_trade,
            price=original.price,
            commission=commission_for_trade,
            executed_at=original.executed_at,
            pnl=original.pnl,  # Note: pnl stays with first split
            currency=original.currency,
            multiplier=original.multiplier,
            origin=EXECUTION_ORIGIN_SPLIT,
            parent_id=original.id,
            trade_id=trade_id,
            strike=original.strike,
            expiry=original.expiry,
            option_type=original.option_type,
            open_close=original.open_close,
        )

        # 5. Create remainder child (for other trades or future allocation)
        remainder_qty = original.quantity - quantity_for_trade
        if remainder_qty > 0:
            remainder_commission = original.commission - commission_for_trade

            await self._exec_repo.create(
                user_id=original.user_id,
                account_id=original.account_id,
                symbol=original.symbol,
                conid=original.conid,
                asset_class=original.asset_class,
                direction=original.direction,
                quantity=remainder_qty,
                price=original.price,
                commission=remainder_commission,
                executed_at=original.executed_at,
                pnl=None,  # Remainder gets no pnl
                currency=original.currency,
                multiplier=original.multiplier,
                origin=EXECUTION_ORIGIN_SPLIT,
                parent_id=original.id,
                trade_id=None,  # Will be assigned by subsequent trades
                strike=original.strike,
                expiry=original.expiry,
                option_type=original.option_type,
                open_close=original.open_close,
            )

        logger.debug(
            "Split execution %s: %s → trade %s, remainder: %s",
            execution_id,
            quantity_for_trade,
            trade_id,
            remainder_qty,
        )

        return child_for_trade

    async def _assign_execution_to_trade(
        self,
        execution_id: uuid.UUID,
        trade_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Directly assign an execution to a trade (no splitting required).

        Args:
            execution_id: ID of the execution to assign.
            trade_id: Target trade ID.
            user_id: Authenticated user ID used for ownership validation.

        Returns:
            True if the assignment was successful, False otherwise.

        Raises:
            TradeNotFoundError: If the trade does not exist for the user.
            ExecutionNotFoundError: If the execution does not exist for the user.
        """
        db_trade = await self._trade_repo.get_by_id(trade_id, user_id)
        if db_trade is None:
            raise TradeNotFoundError(f"Trade {trade_id} not found for user {user_id}.")

        execution = await self._exec_repo.get_by_id(execution_id, user_id=user_id)
        if execution is None:
            raise ExecutionNotFoundError(f"Execution {execution_id} not found for user {user_id}.")

        success = await self._exec_repo.update_trade_id(execution_id, trade_id)

        if success:
            logger.debug(
                "execution_assigned_to_trade execution_id=%s trade_id=%s user_id=%s",
                execution_id,
                trade_id,
                user_id,
            )
        else:
            raise ExecutionNotFoundError(f"Execution {execution_id} not found during trade assignment.")

        return success

    def _validate_split_quantities(
        self,
        original_qty: Decimal,
        allocations: list[ExecutionAllocation],
    ) -> None:
        """Validate that allocation quantities don't exceed the original execution.

        Args:
            original_qty: Original execution quantity.
            allocations: List of execution allocations.

        Raises:
            ExecutionValidationError: If allocation quantities exceed original quantity.
        """
        total_used = sum(alloc.quantity_used for alloc in allocations)
        if total_used > original_qty + (Decimal("0.00000001") * max(1, len(allocations))):
            raise ExecutionValidationError(f"Allocation overflow: total used {total_used} > original {original_qty}")

    def _validate_split_commissions(
        self,
        original_commission: Decimal,
        allocations: list[ExecutionAllocation],
    ) -> None:
        """Validate that allocation commissions don't exceed the original execution.

        Args:
            original_commission: Original execution commission.
            allocations: List of execution allocations.

        Raises:
            ExecutionValidationError: If allocation commissions exceed
                original commission.
        """
        total_used = sum(alloc.commission_used for alloc in allocations)
        if total_used > original_commission + (Decimal("0.00000001") * max(1, len(allocations))):
            raise ExecutionValidationError(f"Commission overflow: total used {total_used} > original {original_commission}")

    async def _validate_split_backfill_consistency(
        self,
        split_inputs: dict[
            uuid.UUID,
            tuple[LogicalExecution, list[tuple[uuid.UUID, ExecutionAllocation]]],
        ],
    ) -> None:
        """Validate split consistency and conservation after backfill writes.

        Args:
            split_inputs: Split parents mapped to original execution and expected
                trade/allocation usage.

        Raises:
            ExecutionValidationError: If any consistency check fails.
        """
        for parent_id, (parent, usage_list) in split_inputs.items():
            children = await self._exec_repo.get_by_parent_id(parent_id)
            if not children:
                raise ExecutionValidationError(f"Split consistency failed: no children found for {parent_id}.")

            expected_trade_ids = {trade_id for trade_id, _ in usage_list}
            child_trade_ids = {child.trade_id for child in children if child.trade_id is not None}

            if child_trade_ids != expected_trade_ids:
                raise ExecutionValidationError(
                    f"Split assignment completeness failed for {parent_id}: expected={len(expected_trade_ids)} actual={len(child_trade_ids)}"
                )

            if any(child.parent_id != parent_id for child in children):
                raise ExecutionValidationError(f"Split lineage integrity failed for {parent_id}.")

            if any(child.origin != EXECUTION_ORIGIN_SPLIT for child in children):
                raise ExecutionValidationError(f"Split integrity failed: non-split child found for {parent_id}.")

            if any(child.trade_id is None for child in children):
                raise ExecutionValidationError(f"Split assignment completeness failed for {parent_id}.")

            expected_quantity = sum(allocation.quantity_used for _, allocation in usage_list)
            expected_commission = sum(allocation.commission_used for _, allocation in usage_list)

            children_quantity = Decimal(sum(child.quantity for child in children))
            children_commission = Decimal(sum(child.commission for child in children))

            quantity_diff = abs(children_quantity - expected_quantity)
            tolerance = Decimal("0.00000001") * Decimal(len(children))
            if quantity_diff > tolerance:
                raise ExecutionValidationError(f"Split quantity conservation failed for {parent_id}: expected={expected_quantity} actual={children_quantity}")

            commission_diff = abs(children_commission - expected_commission)
            if commission_diff > tolerance:
                raise ExecutionValidationError(
                    f"Split commission conservation failed for {parent_id}: expected={expected_commission} actual={children_commission}"
                )

            self._validate_split_quantities(parent.quantity, [a for _, a in usage_list])
            self._validate_split_commissions(parent.commission, [a for _, a in usage_list])

    async def _find_orphaned_children_for_trades(
        self,
        trades_with_sources: list[TradeCreateWithSources],
        user_id: uuid.UUID,
    ) -> int:
        """Detect orphaned split children for accounts involved in this import.

        Args:
            trades_with_sources: Trades processed by backfill.
            user_id: Owning user UUID.

        Returns:
            Number of orphaned split children found.
        """
        account_ids = {
            trade_source.created_trade.account_id
            for trade_source in trades_with_sources
            if trade_source.created_trade is not None and trade_source.created_trade.account_id is not None
        }

        orphaned_count = 0
        for account_id in account_ids:
            orphaned = await self._exec_repo.find_orphaned_children(user_id, account_id)
            orphaned_count += len(orphaned)

        if orphaned_count > 0:
            logger.warning(
                "split_backfill_orphaned_children_detected user_id=%s accounts=%d count=%d",
                user_id,
                len(account_ids),
                orphaned_count,
            )

        return orphaned_count

    async def _resolve_orphaned_children_for_trades(
        self,
        trades_with_sources: list[TradeCreateWithSources],
        user_id: uuid.UUID,
    ) -> int:
        """Resolve orphaned split children by assigning expected trade IDs.

        Args:
            trades_with_sources: Trades processed by backfill.
            user_id: Owning user UUID.

        Returns:
            Number of resolved orphaned child rows.
        """
        expected_trade_ids_by_parent: dict[uuid.UUID | str, list[uuid.UUID]] = {}
        for trade_source in trades_with_sources:
            created_trade = trade_source.created_trade
            if created_trade is None:
                continue
            for allocation in trade_source.source_executions:
                expected_trade_ids_by_parent.setdefault(
                    allocation.execution_id,
                    [],
                ).append(created_trade.id)

        siblings_by_parent: dict[uuid.UUID | str, list[LogicalExecution]] = {}
        unresolved_trade_ids_by_parent: dict[uuid.UUID | str, list[uuid.UUID]] = {}

        account_ids = {
            trade_source.created_trade.account_id
            for trade_source in trades_with_sources
            if trade_source.created_trade is not None and trade_source.created_trade.account_id is not None
        }

        resolved_count = 0
        for account_id in account_ids:
            orphaned_children = await self._exec_repo.find_orphaned_children(
                user_id,
                account_id,
            )
            for orphan in orphaned_children:
                if orphan.parent_id is None:
                    continue
                expected_trade_ids = expected_trade_ids_by_parent.get(
                    orphan.parent_id,
                    [],
                )
                if not expected_trade_ids:
                    continue
                sibling_children = siblings_by_parent.get(orphan.parent_id)
                if sibling_children is None:
                    sibling_children = await self._exec_repo.get_by_parent_id(orphan.parent_id)
                    siblings_by_parent[orphan.parent_id] = sibling_children

                unresolved_trade_ids = unresolved_trade_ids_by_parent.get(orphan.parent_id)
                if unresolved_trade_ids is None:
                    assigned_trade_ids = {child.trade_id for child in sibling_children if child.trade_id is not None}
                    unresolved_trade_ids = [trade_id for trade_id in expected_trade_ids if trade_id not in assigned_trade_ids]
                    unresolved_trade_ids_by_parent[orphan.parent_id] = unresolved_trade_ids
                if not unresolved_trade_ids:
                    continue
                target_trade_id = unresolved_trade_ids.pop(0)
                assigned = await self._exec_repo.update_trade_id(
                    orphan.id,
                    target_trade_id,
                )
                if assigned:
                    resolved_count += 1

        if resolved_count > 0:
            logger.warning(
                "split_backfill_orphaned_children_resolved user_id=%s resolved=%d",
                user_id,
                resolved_count,
            )
        return resolved_count
