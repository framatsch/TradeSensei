## 1. Shared OCC parser

- [x] 1.1 Create `backend/app/utils/occ.py` with `parse_occ_option(symbol) -> (Decimal | None, date | None, str | None)` and `extract_occ_underlying(symbol) -> str`; year window `yy <= 50 → 2000+yy else 1900+yy` matching `frontend/lib/parseOccSymbol.ts`.
- [x] 1.2 Add unit tests for `parse_occ_option` (call, put, equity/non-option, malformed suffix) and for `extract_occ_underlying` parity with the old IBKR behaviour.

## 2. Backend model + schema

- [x] 2.1 Add nullable `strike` (`Numeric(18,8)`), `expiry` (`Date`), `option_type` (`String(1)`) columns to `backend/app/models/logical_execution.py`.
- [x] 2.2 Add the same three columns to `backend/app/models/broker_raw_transaction.py`.
- [x] 2.3 Add `strike`, `expiry`, `option_type` to `BrokerRawTransactionCreate` and `BrokerRawTransactionRead` in `backend/app/schemas/broker_raw_transaction.py`, plus an `option_type` validator (`'C'`/`'P'`/None) mirroring `_validate_open_close`.
- [x] 2.4 Add the three fields to `LogicalExecutionRead` in `backend/app/schemas/execution.py`.

## 3. Backend parsers + service

- [x] 3.1 Refactor `backend/app/utils/parsers/ibkr_xml.py` to import the shared `extract_occ_underlying`/`parse_occ_option`; in both `_parse_trade_element_raw` and `_parse_execution_element_raw` derive strike/expiry/option_type from the OCC symbol before it is reduced to the underlying, and pass them into `BrokerRawTransactionCreate`.
- [x] 3.2 Update `backend/app/utils/parsers/schwab_json.py` to derive strike/expiry/option_type from the option OCC `symbol` and pass them into `BrokerRawTransactionCreate`.
- [x] 3.3 Update `LogicalExecutionService.create_from_raw` in `backend/app/services/logical_execution_service.py` to copy `strike`, `expiry`, `option_type` from the raw record onto the `LogicalExecution`.

## 4. Database migration + backfill

- [x] 4.1 Create one Alembic revision (down_revision = current head) adding the six nullable columns to `logical_executions` and `broker_raw_transactions`.
- [x] 4.2 In the same `upgrade()`, backfill `broker_raw_transactions` option rows from `raw_data->>'symbol'` using `parse_occ_option`.
- [x] 4.3 Backfill `logical_executions` option rows by joining to `broker_raw_transactions` on `logical_executions.source_id = broker_raw_transactions.id`.
- [x] 4.4 Implement `downgrade()` to drop all six columns; verify the migration applies and reverts cleanly against a local DB.

## 5. Backend verification

- [x] 5.1 Add/extend parser tests asserting imported option legs carry the correct strike/expiry/option_type (IBKR and Schwab).
- [x] 5.2 Add a migration/backfill test verifying pre-existing option legs get populated and equity legs stay null.
- [x] 5.3 Run `ruff check`, `ruff format`, and `mypy --strict` on the backend with zero errors.

## 6. API client regeneration

- [x] 6.1 Regenerate the frontend OpenAPI client (openapi-sync) so `LogicalExecutionRead` types include `strike`, `expiry`, `option_type`.
- [x] 6.2 Update `frontend/lib/types.ts` `LogicalExecution` type with the three new fields.

## 7. Frontend trade detail

- [x] 7.1 Add Symbol/Asset Class columns to `frontend/components/trades/ExecutionLegsTable.tsx` gated on `trade.is_combo` (unchanged), and add Strike/Type/Expiry columns gated on "trade has ≥1 leg with non-null `option_type`" (applies to single-option AND COMBO trades), with `—` fallback for non-option/null legs; update `frontend/components/trades/ExecutionRow.tsx` cells.
- [x] 7.2 Update `frontend/components/trades/ExecutionSummaryCard.tsx` to render a human-readable option instrument label from `option_type`/`strike`/`expiry`, keying distinct legs by those fields with `conid` fallback. For standard (non-COMBO) option trades, add a contract label subtitle (e.g. "QQQ 712 Call · Oct 3 2025") to the flat grid layout; omit the label when fields are `null` or the trade has no option legs.

## 8. Frontend chart overlays (DESCOPED — see proposal.md § Descoped)

- [x] ~~8.1 In `frontend/components/charts/TradeChart.tsx` derive per-leg option contracts from the executions' typed fields (fallback to `parseOccSymbol`/`conid` when null).~~ Implemented, then reverted.
- [x] ~~8.2 Render horizontal strike price lines per distinct leg (labeled `<strike><C|P>`), one option chip per distinct leg, per-leg entry/exit markers, and an optional expiry vertical line.~~ Implemented, then reverted.
- [x] ~~8.3 Add a chart-local "Chart layers" popover...~~ Implemented, then reverted. Contract details live on the trade detail page only (tasks 7.1–7.2); the chart shows the plain underlying candlestick chart with the pre-existing generic entry/exit markers.

## 9. Frontend verification

- [x] 9.1 Add/extend Jest + React Testing Library tests for the legs table columns and summary card labels. (Chart toggle-persistence test replaced with a test asserting the option overlay UI is absent — see task 8.)
- [x] 9.2 Run frontend typecheck and lint with zero errors.
- [x] 9.3 Visual/a11y check of the option trade detail page (ui-visual-check).

## 10. Docs + changelog

- [x] 10.1 Update AGENTS.md / api-usage docs if leg response shape guidance needs it.
- [x] 10.2 Append the change to the CHANGELOG `[Unreleased]` section.

## 11. Post-implementation bugfixes (found during real-world verification)

Discovered while re-importing a real IBKR export after tasks 1–10 landed; fixed in the
same session since they blocked correct verification of this change. Full root-cause
analysis recorded in Engram memory (tradesensei project).

- [x] 11.1 Fix combo matching in `backend/app/utils/parsers/aggregator.py::build_combo_positions()`: multiple separately-opened combo positions with the same contract set (e.g. the user scaled into the same spread twice) are now matched FIFO and closing legs are split proportionally across them when closed together — producing one trade per opening order, not a merged position. Added `backend/tests/test_combo_builder.py::test_build_combo_positions_two_opens_split_close_produces_two_trades`.
- [x] 11.2 Fix unbounded trade duplication in `backend/app/services/import_service.py::import_file()`: the raw-pipeline "delete all trades and rebuild" safety net was skipped for the **entire account** whenever any combo position was open, causing fragmented/split single-instrument trades to be re-inserted as duplicates on every re-import. Fixed by scoping the exclusion to just the open combo positions' trade IDs and running the delete **before** execution `trade_id` values are read into memory (`backend/app/repositories/trade_repository.py::delete_by_user_account` gained an `exclude_trade_ids` parameter). Added `backend/tests/test_split_aware_import_integration.py::test_reimport_with_open_combo_does_not_duplicate_split_trades`.
