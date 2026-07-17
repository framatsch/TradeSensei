# Tasks: Bulletproof P&L + open/close lifecycle tests

## 1. Fix the dead cross-import regression test

- [x] 1.1 In `backend/tests/integration/test_pnl_regression.py`, change the unpack from
  `raw_records, cash_transactions, corporate_actions = _parse_raw_files(paths)` to
  `raw_records, corporate_actions = _parse_raw_files(paths)` (2-tuple contract)
- [x] 1.2 Remove the now-unused `cash_transactions` reference; confirm the test still
  imports `aggregate_executions_fifo` and `logical_executions_to_trade_creates`
  from `tests.integration.ground_truth_aggregator` (they are re-exported there)
- [x] 1.3 Verify the test still `pytest.skip`s cleanly when the `TraderJournal_20xx.xml`
  files are absent, and that it no longer raises `ValueError` on unpack when they
  are present (manual/local check with data if available)

## 2. Committed synthetic cross-import seed-lot fixtures (CI-safe)

- [x] 2.1 Create `backend/tests/fixtures/ibkr/seed_open_year1.xml`: one single-instrument
  LONG position that remains **open** at end of file (e.g. BUY 100 @ P, no close),
  plus one position on a symbol that will be split in file 2 (opened here, not closed)
- [x] 2.2 Create `backend/tests/fixtures/ibkr/seed_close_year2.xml`: the closing executions
  for the file-1 positions, plus a `<CorporateAction>` (reverse split) dated between
  the two files so the seed lot must be split-adjusted **before** the close matches.
  Keep structure identical in shape to `synthetic_year2.xml`
- [x] 2.3 Ensure both fixtures parse with zero parser warnings (mirror the assertion in
  `test_aggregator_synthetic_fixture.py::test_fixtures_parse_without_errors`)

## 3. Cross-import seed-lot regression test (DB, CI-safe)

- [x] 3.1 Add `backend/tests/integration/test_cross_import_seed_regression.py`
- [x] 3.2 Import `seed_open_year1.xml` via `ImportService`, commit, then import
  `seed_close_year2.xml`, commit (mirror the sequential pattern in
  `test_aggregator_synthetic_fixture.py::test_sequential_import_matches_ground_truth_synthetic`)
- [x] 3.3 Assert the position opened in file 1 is **closed** by file 2 (no duplicate
  trade; the closed trade corresponds to the seed lot, i.e. it was UPDATEd not
  re-INSERTed as a fresh open+close)
- [x] 3.4 Assert the split-affected seed lot's closed trade has the split-adjusted
  quantity (`× ratio`) and entry price (`÷ ratio`) and correct P&L against the
  adjusted entry
- [x] 3.5 Assert DB yearly realized P&L equals the in-memory ground truth aggregated
  over both files (compare `pnl`/`net_pnl` sums, tolerance `< 0.01`)

## 4. Direct aggregator unit tests for seed lots (no DB)

- [x] 4.1 Add `SeedLotLike` dataclass stubs (mirroring the protocol in `aggregator.py`)
  in `backend/tests/test_aggregator.py` (or a new `test_aggregator_seed_lots.py`)
- [x] 4.2 Test: `seed_open_lots` — a seed LONG lot closed by an incoming opposite
  execution yields a closed `TradeCreate` with `db_trade_id == seed.id`
- [x] 4.3 Test: split on seed lot — a `CorporateActionLike` dated before the closing
  execution adjusts the seed lot (`quantity × ratio`, `entry_price ÷ ratio`); P&L is
  computed against the adjusted entry price
- [x] 4.4 Test: `seed_orphaned_lots` fill — an orphaned persisted close is filled by a
  later opening execution, reconstructing `pnl`/`net_pnl` from the true entry price
  (asserts NO `0.001` sentinel remains on the filled trade)
- [x] 4.5 Test: direction mismatch — a seed lot and an incoming execution with the SAME
  direction do NOT match (position increases, seed lot stays open); an orphaned lot
  whose direction opposes the open lot is left unmatched

## 5. Rewrite the skipped multi-leg VWAP tests to FIFO semantics

- [x] 5.1 In `backend/tests/test_aggregator.py`, rewrite
  `test_vwap_entry_exit_calculation_multi_leg`: remove `@skip`; assert the true FIFO
  result for BUY 100 + BUY 50 + SELL 150 = **two** closed trades (lot1 100, lot2 50),
  each with per-lot gross P&L `(exit − lot_entry) × qty × multiplier` and the
  aggregator's commission proration; correct `opened_at`/`closed_at` per lot
- [x] 5.2 Rewrite `test_vwap_with_multiplier_options_contract`: remove `@skip`; assert
  the single 10-contract lot with partial closes (6 then 4) yields **two** closed
  trades, each `pnl = (exit − 5.50) × qty × 100`, commission prorated, total P&L =
  `150 + 120 = 270` split across the two trades
- [x] 5.3 Rename the tests to reflect FIFO-per-lot semantics (e.g.
  `test_multi_lot_partial_close_*`) and update the misleading VWAP docstrings/comments
  to describe actual per-lot FIFO behaviour
- [x] 5.4 Ensure the rewritten assertions derive expected values from the aggregator's
  documented formula (no hardcoded magic numbers that don't reconcile)

## 6. Combo anomaly P&L isolation + combo/split coexistence

- [x] 6.1 In `backend/tests/test_combo_invariants.py`, add a test using the anomaly
  scenario in `tests/test_data/ibkr/combo_positions.xml`: assert the unmatched combo
  close leaves its position open (`closed_at is None`, `pnl is None`) and contributes
  exactly `0` closed P&L
- [x] 6.2 Assert `SUM(pnl)` over combo + single trades in the combo-aware path equals
  the combo-agnostic ground-truth P&L for the matched portion (anomalous position
  contributes 0; no double-count, no loss)
- [x] 6.3 Add a combo/split coexistence guard: an import containing both a combo order
  and a single-instrument position with a corporate-action split produces total
  realized P&L identical between combo-agnostic and combo-aware paths (extend or add
  a small fixture if `combo_positions.xml` lacks a split)

## 7. Schwab SHORT round-trip lifecycle test

- [x] 7.1 Add (or extend an existing Schwab fixture with) a `SELL_TO_OPEN` +
  `BUY_TO_CLOSE` pair on one symbol in `tests/test_data/schwab/`
- [x] 7.2 In `backend/tests/test_schwab_json_import.py`, add a test importing that pair
  through the pipeline: assert exactly one closed trade, `direction == SHORT`,
  `opened_at`/`closed_at` correct, P&L sign correct (profit when close price < open),
  and P&L equals the in-memory FIFO ground truth

## 8. Verification gates

- [x] 8.1 `uv run ruff check app tests` and `uv run ruff format --check app tests` pass
- [x] 8.2 `uv run mypy app --strict` passes (note: test files are not `--strict`, but the
  rewritten VWAP tests must not introduce `round(Decimal | None)` type errors —
  guard with explicit `assert t.pnl is not None` before rounding)
- [x] 8.3 `uv run pytest` passes, including all new tests; the two previously-skipped
  VWAP tests now RUN and pass; the cross-import seed regression runs in CI
- [x] 8.4 Confirm no production code under `app/` changed except intended (this change is
  tests + fixtures + one test-helper unpack fix only)
- [x] 8.5 `openspec validate bulletproof-pnl-lifecycle-tests --strict` passes
