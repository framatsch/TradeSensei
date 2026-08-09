## 0. Baseline (before any code change)

- [x] 0.1 Capture the current aggregation output for all symbols with corporate actions (`OTLK`, `ATOS`) via `tests/integration/ground_truth_aggregator.py` and store it as the regression baseline.
- [x] 0.2 Record current `quantity`, `entry_price`, `exit_price`, `commission`, `pnl`, `net_pnl` for every trade of those symbols. Every later diff must be explainable by exactly one decision from `design.md`.

## 1. Canonical split adjustment

- [x] 1.1 Extend `app/utils/split_adjust.py` into the single shared implementation: expose a holding-period-aware adjustment used for persisted trade values, and keep the existing execution-before-action adjustment for the chart basis. Both share the same ratio arithmetic and the same effective-date boundary.
- [x] 1.1a Implement the effective-date boundary on the exchange-local calendar date. Resolve the instrument timezone in one place with a documented `America/New_York` default for USD instruments, so the approximation has a single call site to replace once an exchange field exists.
- [x] 1.2 Replace the inline loop in `ExecutionService._re_aggregate_trade` (`execution.py:1019-1025`) with a call into the shared helper, applying the holding-period rule. Verify against the `OTLK` trades closed 2023-05-24: they must remain at `quantity=69`, `entry_price=1.44`.
- [x] 1.3 Replace the ratio arithmetic in `aggregator.py:_apply_split_event` with the shared helper.
- [x] 1.4 Stop scaling `commission` and `source_commission` in `_apply_split_event` (`aggregator.py:1023-1030`).
- [x] 1.5 Load corporate actions once per recalculation batch instead of per trade (`execution.py:1000-1001` currently re-queries inside the per-trade path invoked by `_re_aggregate_symbol_trades`).
- [x] 1.6 Verification: run 0.1 and diff. Only trades held across an effective date may change, and only by the removed commission scaling.

## 2. Dual-basis exposure and impact marker

- [x] 2.1 Add chart-adjusted counterparts of `quantity`, `entry_price`, `exit_price` to the trade read model, derived on read via the shared helper. Do not add DB columns.
- [x] 2.2 Add an affected-by-corporate-action marker to the trade read model, listing the applicable actions.
- [x] 2.3 Assert the invariant in tests: within each basis, the sum of a trade's execution legs equals the trade header.
- [x] 2.4 Surface the marker in the trade detail UI so the difference between header values and chart basis is disclosed rather than inferred.

## 3. Market data cache invalidation

- [x] 3.1 Delete cached `ohlc_prices` rows for the affected symbol on corporate action create, update, and delete. On symbol change, invalidate both the old and the new symbol.
- [x] 3.2 Verification: create a corporate action for a symbol with cached bars, confirm the rows are gone and the next chart request refetches.

## 4. Uniqueness and atomicity

- [x] 4.1 Alembic migration: unique constraint on `corporate_actions (user_id, symbol, date)`. Verify no duplicates exist before applying.
- [x] 4.2 Reject manual create on collision with a conflict response identifying the existing action. Replace `find_by_user_symbol_date_ratio` with a lookup on `(user_id, symbol, date)` so the ratio no longer participates in identity.
- [x] 4.3 Change the import path to update the existing action on collision instead of inserting (`import_service.py:324-332`).
- [x] 4.4 Collapse corporate action CRUD, trade recalculation, and cache invalidation into a single transaction with one commit (`corporate_action_service.py:138-143`, `:174-182`, `:207-210`).

## 5. Remove the dead Schwab CSV parser and the seed-lot path

- [x] 5.1 Delete `app/utils/parsers/schwab.py`. It is unreachable — `factory.py:48-51` wires `BrokerType.SCHWAB` to `SchwabJSONParser`, and the module-private helpers are used nowhere else.
- [x] 5.2 Delete the `SchwabParser` unit tests (`test_import.py:80-174` block) and fix the import at `test_import.py:35`.
- [x] 5.3 Remove the now-unreachable legacy branch in `import_service.py:500-508`, and drop `seed_open_lots` / `seed_orphaned_lots` from the aggregation entry points and `_preload_seed_lots`.
- [x] 5.4 Rewrite `test_aggregator_seed_lots.py` against the logical-execution rebuild path. `test_split_adjusts_seed_open_lot_before_close:113` encodes the seed assumption and must be reformulated, not deleted.
- [x] 5.5 Verification: re-run an import over the existing raw transactions and confirm the resulting trade projection is identical to the baseline from 0.2.

## 6. Tests

- [x] 6.1 Position closed before the effective date is not adjusted (regression for the `OTLK` case).
- [x] 6.2 Position open across the effective date is adjusted exactly once.
- [x] 6.3 Execution on the effective date counts as post-split.
- [x] 6.4 After-hours execution whose UTC date is the effective date but whose exchange-local date is the day before is treated as pre-split.
- [x] 6.5 Commission is unchanged by any corporate action in both engines.
- [x] 6.6 Import path and re-aggregation path produce identical values for the same input.
- [x] 6.7 Corporate action create / update-date / delete each leave pre-split closed trades untouched.
- [x] 6.8 Legs sum to header within each basis.
- [x] 6.9 Corporate action CRUD invalidates cached bars for the symbol.
- [x] 6.10 Duplicate manual create is rejected; two near-identical ratios cannot both persist.
- [x] 6.11 Import updates rather than duplicates an existing action for the same symbol and date.
- [x] 6.12 A failure during recalculation rolls back the corporate action entirely.
- [x] 6.13 Recalculation run repeatedly yields identical values (idempotency).
