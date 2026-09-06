## Why

The project already decided in `2026-04-18-fix-ibkr-pnl-calculation` that broker-reported
P&L must never determine an aggregated `Trade`'s P&L, because `fifoPnlRealized` is an
aggregated mixed value across batched closures. That decision was implemented in the FIFO
aggregator — but `ExecutionService._re_aggregate_trade` still prefers broker leg P&L over
the price-based computation. The requirement that would have caught this was written as a
new `pnl-calculation` capability but never materialised into `openspec/specs/`, so it has
been unenforceable ever since.

The result is two code paths that compute the same value from the same data using different
rules. Import is correct; re-aggregation contradicts it. A user merging two Schwab DIOD trades
got `pnl = 0.00` instead of `-133.90`, which is how the divergence was found.

## What Changes

- Restore `pnl-calculation` as a living capability in `openspec/specs/`, carrying forward the
  requirements accepted in `2026-04-18-fix-ibkr-pnl-calculation` that were never materialised.
- Extend the "ignore broker P&L" rule so it binds **every** path that derives a `Trade`'s P&L
  from its executions — not only `aggregate_executions_fifo`. Re-aggregation must reproduce
  import for identical inputs.
- Remove the broker-P&L preference from the non-combo branch of
  `ExecutionService._re_aggregate_trade`, so gross P&L is always
  `(exit − entry) × qty × multiplier` and net P&L is always `gross − commission`.
- Require that broker-reported P&L is never silently reinterpreted as a closing-leg marker
  outside the FIFO aggregator, and document the Schwab `Decimal("0")` sentinel as an
  aggregator-internal signal.
- Add the missing regression coverage: merging a Schwab trade must yield price-derived P&L.
- Correct the two locally miscalculated trades (DIOD, TGT) after the fix lands.

Not included, deliberately — see `design.md` for the reasoning:
- Combo P&L gross/net semantics (self-consistent across both paths today; a separate defect).
- Prorating broker P&L across split children in `import_service.py`.
- The `open_close` backfill and propagation gaps.

## Capabilities

### New Capabilities
- `pnl-calculation`: How gross and net P&L are derived for an aggregated `Trade` — the exact
  formulas, which inputs are authoritative, and the rule that broker-reported P&L is never
  used as a value. Restores and extends the requirements accepted in
  `2026-04-18-fix-ibkr-pnl-calculation`.

### Modified Capabilities
- `non-destructive-aggregation`: adds the requirement that re-aggregating a trade is
  equivalent to importing it — the two paths must produce identical P&L for identical
  executions.

## Impact

- `backend/app/services/execution.py:1107-1120` — the non-combo P&L branch of
  `_re_aggregate_trade`. Reached from 25 call sites across `execution.py`,
  `trade_service.py` and `corporate_action_service.py`: every leg create/update/delete/
  split/merge/reassign/restore, every trade merge, and every corporate-action replay.
- No database migration, no schema change, no API change. `LogicalExecution.pnl` keeps its
  current meaning and values.
- Behavioural change for existing data: re-aggregating an IBKR trade previously replaced its
  price-derived P&L with the sum of `fifoPnlRealized` (which is net of commission, so the
  commission was then subtracted twice). After this change it stays price-derived. 259 local
  IBKR trades are affected in the sense that they can no longer be corrupted; their stored
  values are already correct.
- Production is unaffected as of 2026-09-03: 0 of 452 trades deviate from the price-derived
  value. Local dev data has 2 (DIOD, TGT).
- Tests: `backend/tests/test_execution_reaggregation.py`,
  `backend/tests/test_execution_service.py`, `backend/tests/test_execution_api.py`
  (baseline 47 passed). No existing test asserts the non-combo broker-P&L preference.
