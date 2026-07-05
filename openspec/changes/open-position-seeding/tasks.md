## 1. DB model — shared `open_position` origin

- [ ] 1.1 Add `EXECUTION_ORIGIN_OPEN_POSITION = "open_position"` to `backend/app/models/logical_execution.py` and include it in `VALID_ORIGINS`; update the module docstring + `origin` column comment to list the new value.
- [ ] 1.2 Create an Alembic migration widening the CHECK constraint on `logical_executions.origin` to include `"open_position"` (DROP + ADD constraint, no data migration).
- [ ] 1.3 Verify the migration applies (`alembic upgrade head`) and rolls back (`alembic downgrade -1`) cleanly.
- [ ] 1.4 Ensure this is the single source of the `open_position` origin + CHECK-constraint delta: the superseded `ibkr-open-positions-import` change is removed (its work moved to `ibkr-open-position-adapter`), so no other change re-declares the origin/constraint.

## 2. Schema — broker-neutral snapshot flag

- [ ] 2.1 Add `is_open_position: bool = Field(default=False, ...)` to `BrokerRawTransactionCreate` in `backend/app/schemas/broker_raw_transaction.py`, documented as broker-neutral ("record is derived from a position snapshot, not a discrete execution").
- [ ] 2.2 The flag is **transient**: consumed only when creating the logical execution (which stamps `origin = "open_position"`). Do NOT add a DB column — the snapshot-replace guard (§4) re-reads provenance from `LogicalExecution.origin`, not from the raw row. Document this in a code comment.

## 3. Service — map flag to origin

- [ ] 3.1 In `backend/app/services/logical_execution_service.py`, change `create_from_raw()` so the hardcoded `origin = EXECUTION_ORIGIN_IMPORTED` becomes `EXECUTION_ORIGIN_OPEN_POSITION` when the source raw record is an open-position snapshot; force `pnl = None` for that branch.
- [ ] 3.2 Confirm `bulk_create_from_raw()` needs no change beyond calling the updated `create_from_raw()` (idempotency still handled upstream by `bulk_upsert`).
- [ ] 3.3 Confirm the FIFO aggregator path (`import_service.py`) treats `open_position` legs as ordinary opening legs (no soft-delete/skip); add an assertion/test rather than new aggregator code. Note the aggregator's instrument key is `(symbol, conid, asset_class)` (`aggregator.py:267`) — `conid=None` for Schwab is fine as long as snapshot and close legs share it.

## 4. Snapshot-replace guard (source-of-truth reconciliation)

- [ ] 4.1 In `import_service.py` re-aggregation prep, when the current import carries `open_position` snapshot legs for an account, remove existing `open_position`-origin legs for the same `(account_id, symbol, conid, asset_class)` that are NOT in the current snapshot set, before seeding the new snapshots. This one rule covers both quantity-changed stale lots (B6) and supersession by a real `imported` opening execution (B8). Keep it out of the aggregator core.
- [ ] 4.2 Within the same instrument, if both an `open_position` leg and a real `imported` opening leg are present, the `imported` leg wins (drop the `open_position` leg) so the real fill time/price is authoritative.
- [ ] 4.3 Ensure the shared-id path (IBKR) collapses via `bulk_upsert` before the guard runs (the guard is a safety net, not the primary IBKR mechanism).
- [ ] 4.4 Scope the removal strictly to `open_position`-origin legs — never touch `imported`/`manual`/`merged`/`split` executions.

## 5. Tests (broker-neutral)

- [ ] 5.1 Unit test: a `BrokerRawTransactionCreate` with `is_open_position=True` yields `LogicalExecution(origin="open_position", pnl=None)`; without the flag yields `origin="imported"`.
- [ ] 5.2 Unit test: `"open_position"` is in `VALID_ORIGINS`; a `LogicalExecution` with that origin passes the CHECK constraint (in-memory or migration-backed).
- [ ] 5.3 Integration test: a single flagged snapshot record → open-lot `Trade` (no `closed_at`, no `exit_price`), visible as open.
- [ ] 5.4 Integration test (reconciliation, shared id): snapshot open + later real opening execution with the same raw `id` → one open lot (no duplicate opening leg).
- [ ] 5.5 Integration test (reconciliation, no shared id): snapshot open + later `imported` opening execution overlapping it → guard drops the snapshot leg → one open lot.
- [ ] 5.5a Integration test (snapshot-replace, quantity change): seed `open_position` at Q1, re-import with the same instrument at Q2 → the Q1 leg is removed, one `open_position` lot at Q2 remains.
- [ ] 5.5b Integration test (snapshot-replace, omission): seed `open_position` for instrument X, re-import a snapshot set that omits X → the X `open_position` leg is removed.
- [ ] 5.5c Guard isolation: confirm `imported`/`manual`/`merged`/`split` legs are never removed by the snapshot-replace guard.
- [ ] 5.6 Integration test (close): snapshot open + later closing execution for the same instrument `(symbol, conid, asset_class)` in the opposite direction → one round-trip `Trade` with `opened_at` and `closed_at`.
- [ ] 5.7 Re-import idempotency: importing the same snapshot twice creates no duplicate raw/logical records.

## 6. Documentation

- [ ] 6.1 Document the contract in the relevant backend doc/AGENTS reference: what `is_open_position` means, the `open_position` origin, and the adapter responsibility (deterministic id + UTC `executed_at`).
- [ ] 6.2 Note the approximate-`opened_at` caveat for id-less brokers (holding-period stats skewed; round-trip P&L unaffected).

## 7. Cross-change coordination

- [ ] 7.1 Remove the superseded `ibkr-open-positions-import` change (its parser + keys now live in `ibkr-open-position-adapter`, which depends on this contract). Confirm no duplicate `open_position` origin / `raw-transaction-layer` delta remains.
- [ ] 7.2 Confirm `schwab-positions-cli-import`'s "positions are not imported" Non-Goal points at this capability / `schwab-open-position-adapter` as the follow-up consumer of `positions[]`; do not implement Schwab parsing here.

## 8. Verification

- [ ] 8.1 Run `lint-check` (ruff + `mypy --strict`) — zero new errors.
- [ ] 8.2 Run `unit-test` (pytest) for the new open-position seeding + reconciliation tests; confirm green.
