# Tasks: Leg-native COMBO import

## 1. Backend — `open_close` field (both brokers)

- [x] 1.1 Add `open_close: str | None` to `BrokerRawTransactionCreate` in `app/schemas/broker_raw_transaction.py` (allowed values `"O"`, `"C"`, `None`)
- [x] 1.2 Add nullable `open_close` column to the `LogicalExecution` ORM model in `app/models/logical_execution.py`
- [x] 1.3 Create an Alembic migration adding `logical_executions.open_close` (nullable String(1)) with `down_revision = "c1f0baf3b07d"`
- [x] 1.4 IBKR parser (`app/utils/parsers/ibkr_xml.py`): derive `open_close` from `openCloseIndicator` (`"O"` when contains O not C, `"C"` when contains C not O, else `None`) in both `_parse_trade_element_raw` and `_parse_execution_element_raw`
- [x] 1.5 Schwab parser (`app/utils/parsers/schwab_json.py`): derive `open_close` from the primary leg's `positionEffect` (`OPENING` → `"O"`, `CLOSING` → `"C"`, else `None`) and set it on the raw record
- [x] 1.6 `app/services/logical_execution_service.py` `create_from_raw`: copy `raw.open_close` onto the new `LogicalExecution` (keep `is_mixed_execution` derivation unchanged)
- [x] 1.7 Expose `open_close` in `LogicalExecutionRead` (`app/schemas/execution.py`)
- [x] 1.8 Unit test: IBKR `openCloseIndicator` → `open_close` mapping (O / C / mixed→null)
- [x] 1.9 Unit test: Schwab `positionEffect` → `open_close` mapping (OPENING / CLOSING / absent→null)

## 2. Backend — combo raw-data lookup

- [x] 2.1 Add `get_combo_order_meta_by_raw_ids(raw_ids)` to `BrokerRawTransactionRepository` returning per raw id: `brokerageOrderID` and `netCash` (JSONB extraction, single query); returns `{}` for empty input
- [x] 2.2 Unit test for the repository method (mocked session or integration)

## 3. Backend — combo builder (detection + leg binding)

- [x] 3.1 Add a `build_combo_positions()` function in `app/utils/parsers/aggregator.py` (or a new `combo.py`) that takes execution `TradeCreate`s enriched with `broker_order_id`, `open_close`, `broker_conid`, `netCash`, and `source_execution_id`
- [x] 3.2 Partition executions: combo-eligible = order groups (`broker_order_id`) with ≥2 distinct `conid`s; everything else returned unchanged for FIFO
- [x] 3.3 Build open combo positions from all-`O` combo orders (contract set = distinct conids; record per-contract quantities)
- [x] 3.4 Match all-`C` combo orders to open positions by **exact** contract set + per-contract quantity (FIFO across positions); attach closing legs
- [x] 3.5 Emit one COMBO `TradeCreate` per position: `is_combo=True`, header fields null, `commission=SUM(legs)`, `opened_at=MIN(O)`, `closed_at=MAX(C)` if fully closed, `pnl=SUM(C.pnl)` if any, `net_pnl=pnl−commission`
- [x] 3.6 Derive combo `direction` from net opening cash flow (`SUM(open_leg.netCash)`: debit→LONG, credit→SHORT)
- [x] 3.7 Return the set of leg `source_execution_id`s per COMBO trade so the import service can bind `LogicalExecution.trade_id`
- [x] 3.8 Anomaly handling: a combo-eligible closing order that fails exact contract-set/quantity matching emits a warning (offending `brokerageOrderID`, expected vs. received contract set) and leaves the open COMBO position open; legs are NOT rerouted into single-instrument FIFO (Decision 6)
- [x] 3.9 Create a new dedicated fixture `tests/test_data/ibkr/combo_positions.xml` with anonymized combo examples extracted from `tmp/TradeSensei.xml` (gitignored, not usable directly): the QQQ 712C/722C vertical (fully closed, 4 legs), the META 620C/640C vertical (multiple partial open/close order pairs across the same underlying), and the XSP 744C/755C vertical (fully closed). Anonymize `accountId`, keep `brokerageOrderID`/`conid`/`openCloseIndicator`/`netCash`/`fifoPnlRealized` structurally intact so the combo builder can be exercised end-to-end. Do NOT modify `tests/test_data/ibkr/TraderJournal_anonymized_combined.xml` (that fixture stays single-instrument-only to keep `test_import_ground_truth.py`'s strict `db_yearly == gt_yearly` trade-count comparison valid, since `ground_truth_aggregator.py` intentionally has no combo awareness)
- [x] 3.10 Unit tests against `combo_positions.xml`: open-only combo, fully-closed combo (4 legs), unmatched-close anomaly (warning + combo stays open), direction (debit/credit) for each of the QQQ/META/XSP examples

## 4. Backend — cross-import seed positions

- [x] 4.1 Add `list_open_combo_positions_by_user(user_id, portfolio_id, account_id)` to `TradeRepository` returning open COMBO trades with their non-deleted opening legs (contract set = distinct conids of opening legs)
- [x] 4.2 Feed seed combo positions into `build_combo_positions()` so later closing orders match and close the existing COMBO trade
- [x] 4.3 Carry the existing `db_trade_id` on the resulting COMBO close so the import service issues an UPDATE (close) instead of INSERT
- [x] 4.4 Integration test: split `combo_positions.xml`'s QQQ vertical into an opening-only file (import A) and a closing-only file (import B); verify import B updates the existing open COMBO trade to closed rather than creating a duplicate

## 5. Backend — import service wiring

- [x] 5.1 In `ImportService._iter_trade_creates_from_logical_batches`, enrich each `TradeCreate` with `broker_order_id`, `open_close`, and `netCash` from the raw layer (batch lookup from Task 2.1)
- [x] 5.2 In `import_file` raw pipeline, partition combo-eligible executions and route them to `build_combo_positions()`; route the rest to the existing FIFO path unchanged
- [x] 5.3 Persist COMBO trades and bind all their legs (`LogicalExecution.trade_id = COMBO.id`); persist FIFO trades and run the existing split-aware backfill unchanged
- [x] 5.4 Handle combo UPDATE (cross-import close) via `db_trade_id`, reusing the seed-lot UPDATE convention
- [x] 5.5 Ensure combo legs are excluded from the FIFO input so they are never double-counted
- [x] 5.6 Integration test importing `tests/test_data/ibkr/combo_positions.xml` via the public upload API: verify each combo becomes a single COMBO trade with the correct leg count and P&L, and confirm `test_import_ground_truth.py` (on its unmodified fixture) still passes unchanged

## 6. Backend — P&L-preservation invariant (combo grouping must not change total P&L)

- [x] 6.1 Add a combo-aware yearly aggregation helper alongside `ground_truth_aggregator.py` (e.g. `aggregate_files_yearly_with_combos`) that runs the SAME parse + FIFO path but additionally applies the combo builder, so the two can be diffed
- [x] 6.2 Differential unit test on `combo_positions.xml`: assert `SUM(pnl)` (DB-scale quantized) is **bit-identical** between the combo-agnostic path (`aggregate_files_yearly`) and the combo-aware path — grouping is purely presentational and MUST NOT change any P&L total
- [x] 6.3 Per-combo invariant unit test: for each emitted COMBO trade, assert `trade.pnl == SUM(fifoPnlRealized of its bound legs)` and `trade.commission == SUM(leg.commission)`
- [x] 6.4 Integration (DB) P&L-anchor test: import `combo_positions.xml` via the API, then assert `SUM(DB trade net_pnl over combo + single trades)` per year equals the combo-agnostic `ground_truth_aggregator` P&L per year (compare the `pnl` field only, NOT `trades` count, since grouping changes the count but not the sum)
- [x] 6.5 Anomaly case: confirm that an unmatched combo close (Decision 6) leaves the position open and therefore contributes NO closed P&L, and that no P&L is double-counted or lost

## 7. Backend — combo re-aggregation parity

- [x] 7.1 Verify the existing combo re-aggregation (from `combo-positions`) applies to imported combos: skip VWAP, `pnl=SUM(leg.pnl)`, `commission=SUM`, `opened_at=MIN`, `closed_at=MAX`
- [x] 7.2 Unit test: re-aggregating an imported COMBO keeps header fields null and recomputes pnl/commission from legs

## 8. Frontend — legs table + summary card

- [x] 8.1 Add an `Open/Close` column to the execution legs table for COMBO trades (renders `open_close` as Open/Close/—; hidden for non-COMBO)
- [x] 8.2 Update `ExecutionSummaryCard` grouping key to `(symbol, asset_class, conid)` so distinct strikes show as separate rows
- [x] 8.3 Ensure `open_close` is consumed from the regenerated API client (run openapi-sync after backend schema change)
- [x] 8.4 Component test: legs table renders Open/Close column and per-contract rows for a COMBO vertical

## 9. Regeneration + docs

- [x] 9.1 Regenerate the frontend OpenAPI client (`/openapi-sync`) after the `LogicalExecutionRead.open_close` change
- [x] 9.2 Update `docs/api-usage.md` / AGENTS.md notes if the import behaviour section references combos
- [x] 9.3 Append CHANGELOG `[Unreleased]` entry

## 10. E2E

- [x] 10.1 Seed a fully-closed COMBO vertical and add a Playwright test asserting: COMBO badge present, legs table has Open/Close column, four leg rows (2 open, 2 close), summary card shows two contract rows

## 11. Verification gates

- [x] 11.1 `uv run ruff check app tests` and `uv run ruff format --check app tests` pass
- [x] 11.2 `uv run mypy app --strict` passes
- [x] 11.3 `uv run pytest` (unit + integration) passes, including new combo tests and the P&L-preservation invariant tests (Task 6)
- [x] 11.4 `openspec validate combo-import-leg-model --strict` passes
