"""Business-logic service for broker file import operations.

Orchestrates broker file parsing and bulk trade creation for a given
account.  No HTTP concepts appear in this layer.
"""

import logging
import uuid
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AccountNotFoundError
from app.models.corporate_action import CorporateAction
from app.repositories.account_repository import AccountRepository
from app.repositories.broker_raw_transaction_repository import (
    BrokerRawTransactionRepository,
)
from app.repositories.cash_transaction_repository import CashTransactionRepository
from app.repositories.corporate_action_repository import CorporateActionRepository
from app.repositories.trade_repository import TradeRepository
from app.schemas.broker_raw_transaction import BrokerRawTransactionCreate
from app.schemas.cash_transaction import CashTransactionCreateRequest
from app.schemas.imports import ImportResult
from app.services.cash_transaction_service import CashTransactionService
from app.services.logical_execution_service import LogicalExecutionService
from app.utils.parsers.aggregator import (
    CorporateActionLike,
    ExecutionLike,
    SeedLotLike,
    aggregate_executions_fifo,
    logical_executions_to_trade_creates,
)
from app.utils.parsers.base import BrokerParser
from app.utils.parsers.factory import BrokerType, get_parser

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
        self._raw_repo = BrokerRawTransactionRepository(session)
        self._logical_svc = LogicalExecutionService(session)

    async def import_file(
        self,
        content: bytes,
        filename: str,
        broker: BrokerType,
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
        if account_id is not None:
            account = await self._account_repo.get_by_id(account_id, user_id)
            if account is None:
                raise AccountNotFoundError(
                    f"Account {account_id} not found for user {user_id}."
                )

        # Load corporate actions for this user so the parser/aggregator can apply
        # split adjustments at the correct chronological point.
        corporate_actions = await self._ca_repo.list_by_user(user_id)

        # Load all existing open lots for this user so the aggregator can match
        # incoming closing executions against them (cross-period import support).
        open_lots = await self._trade_repo.list_open_lots_by_user(user_id)
        open_lot_ids = {lot.id for lot in open_lots}

        # Load all existing orphaned lots (closed, but no entry leg).
        orphaned_lots = await self._trade_repo.list_orphaned_lots_by_user(user_id)
        orphaned_lot_ids = {lot.id for lot in orphaned_lots}

        # Load the set of (broker_conid, opened_at) keys for manually-edited trades.
        manually_edited_keys = (
            await self._trade_repo.list_manually_edited_keys(user_id)
            if not overwrite_manually_edited
            else set()
        )

        # Load existing execution keys for deduplication to ensure idempotency.
        existing_entry_keys = await self._trade_repo.list_existing_entry_keys(
            user_id, account_id
        )
        existing_close_keys = await self._trade_repo.list_existing_close_keys(
            user_id, account_id
        )

        parser: BrokerParser = get_parser(broker)

        ca_for_parser: Sequence[CorporateActionLike] | None = (
            cast(Sequence[CorporateActionLike], corporate_actions)
            if corporate_actions
            else None
        )
        seed_for_parser: Sequence[SeedLotLike] | None = (
            cast(Sequence[SeedLotLike], open_lots) if open_lots else None
        )

        parser_warnings: list[str] = []
        parsed_cash_txs: list[CashTransactionCreateRequest] = []

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
                and (len(raw_parse_result) == 2 or len(raw_parse_result) == 3)
                and isinstance(raw_parse_result[0], list)
                and isinstance(raw_parse_result[1], list)
            ):
                if len(raw_parse_result) == 2:
                    raw_records, parsed_cash_txs = raw_parse_result
                    parsed_corporate_actions = []
                else:
                    raw_records, parsed_cash_txs, parsed_corporate_actions = (
                        raw_parse_result
                    )
                use_raw_pipeline = True
            else:
                use_raw_pipeline = False

        if use_raw_pipeline:
            for ca in parsed_corporate_actions:
                existing = await self._session.execute(
                    select(CorporateAction).where(
                        CorporateAction.user_id == user_id,
                        CorporateAction.symbol == ca.symbol,
                        CorporateAction.date == ca.date,
                        CorporateAction.ratio == ca.ratio,
                    )
                )
                if not existing.scalar_one_or_none():
                    await self._ca_repo.create(ca.to_corporate_action_create(user_id))

            # Reload corporate actions after adding new ones from the file
            corporate_actions = await self._ca_repo.list_by_user(user_id)
            ca_for_parser = (
                cast(Sequence[CorporateActionLike], corporate_actions)
                if corporate_actions
                else None
            )

            # Stamp user_id / account_id onto each raw record.
            stamped_raw: list[BrokerRawTransactionCreate] = []
            for rec in raw_records:
                # Prepend user_id to ensure the execution ID is globally unique
                # across all users (idempotent per user).
                new_id = (
                    rec.id
                    if rec.id.startswith(f"{user_id}:")
                    else f"{user_id}:{rec.id}"
                )
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

            await self._logical_svc.bulk_create_from_raw(new_orm_raws)
            await self._session.flush()

            # Load ALL logical executions for this user/account (including those
            # from previous imports) so the aggregator can match cross-period
            # positions.
            all_logical = await self._logical_svc.list_by_user(
                user_id, account_id=account_id
            )
            parsed_trades = logical_executions_to_trade_creates(
                cast(list[ExecutionLike], all_logical)
            )

            # Run FIFO aggregation from the logical layer only.
            # Do not seed with existing trades in DB; for raw-pipeline imports we
            # rebuild the trade projection from logical executions.
            parsed_trades = aggregate_executions_fifo(
                parsed_trades,
                corporate_actions=ca_for_parser,
                seed_open_lots=None,
                seed_orphaned_lots=None,
            )
        else:
            # ── Legacy pipeline (fallback) ────────────────────────────────────
            parsed_trades, parsed_cash_txs = parser.parse(
                content,
                filename,
                corporate_actions=ca_for_parser,
                seed_open_lots=seed_for_parser,
                seed_orphaned_lots=cast(Sequence[SeedLotLike], orphaned_lots)
                if orphaned_lots
                else None,
            )

        # Enrich pnl_eur — base class provides a no-op default so this is always safe.
        await parser.enrich_pnl_eur(parsed_trades, self._session)

        # Collect parser warnings (IBKRParser / SchwabParser expose .warnings).
        parser_warnings += getattr(parser, "warnings", [])

        trades_created = 0
        trades_updated = 0
        trades_skipped_manually_edited = 0
        cash_txs_created = 0
        create_warnings: list[str] = []
        raw_projection_rebuild = use_raw_pipeline and account_id is not None

        if raw_projection_rebuild and account_id is not None:
            await self._trade_repo.delete_by_user_account(
                user_id=user_id,
                account_id=account_id,
                include_manually_edited=overwrite_manually_edited,
            )
        # Track db_trade_ids that have already been updated once.  If the same
        # seed lot appears more than once in parsed_trades (partial close split),
        # the first occurrence issues an UPDATE; subsequent occurrences become
        # INSERTs (new rows for the partial-close slices).
        already_updated_ids: set[uuid.UUID] = set()

        for trade_data in parsed_trades:
            if raw_projection_rebuild:
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
                    msg = (
                        f"Failed to persist trade {trade_data.symbol} "
                        f"opened at {trade_data.opened_at}: {exc}"
                    )
                    logger.warning(msg)
                    create_warnings.append(msg)
                continue

            db_trade_id = trade_data.db_trade_id

            # --- Case 1: This result closes an existing open DB lot (UPDATE) ---

            if db_trade_id is not None and (
                db_trade_id in open_lot_ids or db_trade_id in orphaned_lot_ids
            ):
                is_orphan = db_trade_id in orphaned_lot_ids
                # Check for manual-edit protection on the original open lot
                match_key = (trade_data.broker_conid, trade_data.opened_at)
                if match_key in manually_edited_keys:
                    logger.debug(
                        "Skipping close of manually-edited trade: "
                        "symbol=%s opened_at=%s",
                        trade_data.symbol,
                        trade_data.opened_at,
                    )
                    trades_skipped_manually_edited += 1
                    continue

                # Only update/insert if the trade is actually closed now
                if (
                    trade_data.closed_at is not None
                    and trade_data.exit_price is not None
                    and trade_data.entry_price != Decimal("0.001")
                ):
                    if db_trade_id not in already_updated_ids:
                        # First close of this seed lot — UPDATE the original row.
                        try:
                            if is_orphan:
                                await self._trade_repo.fill_orphaned_lot(
                                    trade_id=db_trade_id,
                                    entry_price=trade_data.entry_price,
                                    opened_at=trade_data.opened_at,
                                    pnl=trade_data.pnl,
                                    pnl_eur=trade_data.pnl_eur,
                                    net_pnl=trade_data.net_pnl,
                                    net_pnl_eur=trade_data.net_pnl_eur,
                                    commission_add=trade_data.commission,
                                    quantity=trade_data.quantity,
                                )
                            else:
                                await self._trade_repo.close_open_lot(
                                    trade_id=db_trade_id,
                                    exit_price=trade_data.exit_price,
                                    closed_at=trade_data.closed_at,
                                    pnl=trade_data.pnl,
                                    pnl_eur=trade_data.pnl_eur,
                                    net_pnl=trade_data.net_pnl,
                                    net_pnl_eur=trade_data.net_pnl_eur,
                                    commission_add=trade_data.commission,
                                    quantity=trade_data.quantity,
                                )
                            already_updated_ids.add(db_trade_id)
                            trades_updated += 1
                        except Exception as exc:  # noqa: BLE001
                            msg = (
                                f"Failed to close/fill open/orphaned lot {db_trade_id} "
                                f"({trade_data.symbol}): {exc}"
                            )
                            logger.warning(msg)
                            create_warnings.append(msg)
                    else:
                        # Subsequent partial close of same seed lot — INSERT a
                        # new row so the full close history is preserved.
                        trade_with_owner = trade_data.model_copy(
                            update={"account_id": account_id, "user_id": user_id}
                        )
                        try:
                            await self._trade_repo.create(trade_with_owner)
                            trades_created += 1
                        except Exception as exc:  # noqa: BLE001
                            msg = (
                                f"Failed to insert partial close for "
                                f"{trade_data.symbol} "
                                f"closed at {trade_data.closed_at}: {exc}"
                            )
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
                            msg = (
                                f"Failed to insert remaining open/orphaned lot for "
                                f"{trade_data.symbol}: {exc}"
                            )
                            logger.warning(msg)
                            create_warnings.append(msg)
                    # If not in already_updated_ids, it means the seed lot wasn't
                    # touched. Skip (already in DB).
                continue

            # --- Case 2: Seed lot that is still open — skip (already in DB) ---
            if (
                db_trade_id is not None
                and db_trade_id not in open_lot_ids
                and db_trade_id not in orphaned_lot_ids
            ):
                # db_trade_id set but not in open_lot_ids — shouldn't happen, skip
                logger.debug(
                    "Skipping seed lot with unknown db_trade_id=%s", db_trade_id
                )
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
                    "Skipping re-import of manually-edited trade: "
                    "symbol=%s opened_at=%s",
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
            if is_orphan:
                # For orphaned trades, the 'opened_at' is actually the
                # execution time of the close leg.
                if trade_data.exit_price is not None:
                    close_key = (
                        trade_data.symbol,
                        trade_data.opened_at,
                        trade_data.exit_price,
                        trade_data.quantity,
                        trade_data.direction.value,
                    )
            else:
                # For regular trades that are closed, closed_at is the
                # execution time of the close leg.
                close_key = (
                    (
                        trade_data.symbol,
                        trade_data.closed_at,
                        trade_data.exit_price,
                        trade_data.quantity,
                        trade_data.direction.value,
                    )
                    if trade_data.closed_at and trade_data.exit_price is not None
                    else None
                )

            if close_key is not None and close_key in existing_close_keys:
                logger.debug(
                    "Skipping duplicate close execution: symbol=%s close_time=%s",
                    trade_data.symbol,
                    close_key[1],
                )
                continue

            # Stamp both account_id and user_id onto each trade before persisting.
            trade_with_owner = trade_data.model_copy(
                update={"account_id": account_id, "user_id": user_id}
            )
            try:
                await self._trade_repo.create(trade_with_owner)
                trades_created += 1
            except Exception as exc:  # noqa: BLE001
                msg = (
                    f"Failed to persist trade {trade_data.symbol} "
                    f"opened at {trade_data.opened_at}: {exc}"
                )
                logger.warning(msg)
                create_warnings.append(msg)

        if account_id is not None:
            for cash_tx_data in parsed_cash_txs:
                # Duplicate check: same account + date + type + amount + symbol
                is_dup = await CashTransactionRepository.find_duplicate(
                    self._session,
                    account_id=account_id,
                    date=cash_tx_data.date,
                    tx_type=cash_tx_data.type,
                    amount=cash_tx_data.amount,
                    symbol=cash_tx_data.symbol,
                )
                if is_dup:
                    logger.debug(
                        "Skipping duplicate cash transaction: %s %s @ %s",
                        cash_tx_data.type,
                        cash_tx_data.symbol,
                        cash_tx_data.date,
                    )
                    continue

                try:
                    await CashTransactionService.create(
                        self._session, user_id, account_id, cash_tx_data
                    )
                    cash_txs_created += 1
                except Exception as exc:  # noqa: BLE001
                    msg = (
                        f"Failed to persist cash transaction "
                        f"at {cash_tx_data.date}: {exc}"
                    )
                    logger.warning(msg)
                    create_warnings.append(msg)

        all_warnings = parser_warnings + create_warnings

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
        cash_txs_skipped = len(parsed_cash_txs) - cash_txs_created

        return ImportResult(
            broker=str(broker),
            filename=filename,
            trades_parsed=new_trades_parsed,
            trades_created=trades_created,
            trades_skipped=trades_skipped,
            cash_transactions_parsed=len(parsed_cash_txs),
            cash_transactions_created=cash_txs_created,
            cash_transactions_skipped=cash_txs_skipped,
            warnings=all_warnings,
        )
