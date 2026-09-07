## 1. Characterisation tests (write first, they must fail)

- [x] 1.1 Aggregator unit test: an opening leg excluded from the input plus a closing leg whose contract is in `protected_contracts` currently yields `[]` — assert the *desired* outcome (one closed trade) so the test fails until section 3 lands
- [x] 1.2 Import integration test: open trade + note + re-import with closing execution — assert `closed_at`, `exit_price`, `pnl`, `net_pnl` are set and the closing `logical_execution` has `trade_id` set
- [x] 1.3 Import integration test: the account's trade row count is unchanged after the close-by-import (guards the seed-lot leak in design.md Risks)
- [x] 1.4 Import integration test: a *closed* protected trade still behaves exactly as today — executions excluded, no field update, incoming close left unlinked, `has_unlinked_executions=true`

## 2. Protection snapshot split by trade state

- [x] 2.1 Extend `ProtectedExecutionSnapshot` (`import_service.py:90`) to carry open and closed protected trades separately
- [x] 2.2 Update `_resolve_protected_execution_snapshot` (`import_service.py:1695`) to partition on `Trade.closed_at IS NULL`; add the repository query needed to resolve trade state alongside the contract refs
- [x] 2.3 Restrict `excluded_execution_ids` passed to `_collect_trade_creates_from_logical_batches` to legs of *closed* protected trades only
- [x] 2.4 Restrict `protected_contracts` passed to `aggregate_executions_fifo_with_sources` to contracts held by *closed* protected trades only

## 3. Seed lots for open protected trades

- [x] 3.1 Add `_build_seed_execution_trades_for_open_protected_trades`, modelled on `_build_seed_combo_execution_trades` (`import_service.py:1795`): build `TradeCreate` rows from the trade's non-deleted legs with `db_trade_id` and `source_execution_id` set, reading values from `logical_executions`
- [x] 3.2 Feed the seeds into the aggregation input alongside the combo seeds
- [x] 3.3 Add the open protected trade IDs to `preserved_trade_ids` / `exclude_trade_ids` so `delete_by_user_account` never sees them
- [x] 3.4 Guard: an unmatched seed lot must not emit a new trade row from `_finalize_open_lots` — recognise seeds by `db_trade_id` and route them to a no-op
- [x] 3.5 Guard: seeded executions' stored values are never written back
- [x] 3.6 Adjust `_backfill_execution_trade_links` (`import_service.py:1198`) so a seeded execution cannot be moved to another trade, while the new closing leg can be attached to the seeded trade
- [x] 3.7 Verify tests 1.1–1.4 now pass

## 4. Update path for protected trades

- [x] 4.1 Replace the "skip protected trade" branch (`import_service.py:584-594`) with: closed protected → skip as today; open protected with a matched seed → apply the update
- [x] 4.2 Replace the `exclude={...}` / `exclude_unset=True` update at `import_service.py:596-601` with an explicit allow-list of broker- and aggregate-derived fields
- [x] 4.3 Add a guard test asserting every `Trade` column is classified as either metadata or broker-derived, so a newly added column fails the build until classified
- [x] 4.4 Regression test: a trade carrying journal, rating, playbook, tradingview link, image URLs, a note, a taxonomy and an annotation retains all of them across a close-by-import

## 5. Partial and over-close behaviour

- [x] 5.1 Test: seeded quantity 10, closing quantity 4 → trade closes 4, remaining 6 stays open, both legs linked
- [x] 5.2 Test: seeded quantity 3, closing quantity 5 → 3 matched, 2 follow ordinary orphan-lot rules, warning names contract and remainder
- [x] 5.3 Confirm split-adjusted seeds behave correctly when a corporate action falls between open and close

## 5b. Manual-close stand-in behaviour (no silent phantom trade)

- [x] 5b.1 Characterisation test: imported opening leg + manual full close + later import of the real broker close currently yields two trade rows, the second with `entry_price=0.001`, and reports `unlinked=0, warnings=[]` — assert the desired outcome so it fails until 5b.3 lands
- [x] 5b.2 Add a repository query resolving `(symbol, conid)` pairs held by a trade that has a non-deleted `origin='manual'`, `source_id IS NULL` leg, scoped to user and account
- [x] 5b.3 Feed those contracts into the aggregator's suppression set alongside the closed-protected contracts (`aggregator.py:683` and `:815`); leave ordinary orphan-lot creation intact for every other contract
- [x] 5b.4 Test: suppression fires when `Trade.is_manually_edited` is `false` (covers the `partial_close_trade` full-close path, `trade_service.py:919-975`)
- [x] 5b.5 Test: a manual leg with `source_id` set does **not** suppress — the ordinary sentinel orphan lot is still created
- [x] 5b.6 Integration test: after the import, `T.has_unlinked_executions` is `true`, `ImportResult` counts the execution as unlinked and carries a warning naming symbol and execution time
- [x] 5b.7 Integration test: deleting the manual leg and re-aggregating links the broker execution to `T`, sets `T.exit_price` to the broker price and clears `has_unlinked_executions`
- [x] 5b.8 Integration test: linking the manual leg via `POST /api/v1/executions/{id}/link` and re-aggregating leaves no duplicate leg on `T` and clears `has_unlinked_executions`
- [x] 5b.9 Test: the account's trade row count is unchanged across the whole scenario (no phantom row ever persisted)

## 6. Marker semantics

- [x] 6.1 Remove `mark_user_modified_for_trade()` from `note_service.py:85-86, 115-116, 140-141`
- [x] 6.2 Remove `mark_user_modified_for_trade()` from `trade_metadata_service.py:77-159` (all five call sites)
- [x] 6.3 Remove `mark_user_modified_for_trade()` from `trade_service.py:599-600` (trade update)
- [x] 6.4 Remove `mark_user_modified_for_trade()` from `trade_service.py:864-865` (trade merge)
- [x] 6.5 Confirm `mark_manually_edited()` remains on every one of those paths
- [x] 6.6 Tests: note, tag, rating, trade update and trade merge each set `is_manually_edited=true` and leave every leg at `user_modified=false`
- [x] 6.7 Test: a trade protected only by a note is still not deleted by `delete_by_user_account` with `overwrite_manually_edited=false`
- [x] 6.8 Test: `PATCH /api/v1/executions/{id}` still sets `user_modified=true`

## 7. Data migration

- [x] 7.1 Create a data-only Alembic migration clearing `user_modified` per the rule in design.md D5
- [x] 7.2 Log every row that does not qualify and is therefore left marked
- [x] 7.3 Assert the migration does not touch `Trade.is_manually_edited`
- [x] 7.4 Test idempotency — second run changes nothing
- [x] 7.5 Run against a copy of production data; expected result: 63 rows cleared, 0 skipped
- [x] 7.6 After the migration, verify ATOS and META still aggregate correctly now that their split children are purgeable again (design.md Open Question 3)

## 8. Import result reporting

- [x] 8.1 Add a "protected positions closed" count to `ImportResult` (`backend/app/schemas/imports.py`)
- [x] 8.2 Ensure executions linked via a seed lot are excluded from `unlinked_executions`
- [x] 8.3 Test: an import that only closes a protected position reports one protected close and zero unlinked executions
- [x] 8.4 Manual stand-in case: set `has_unlinked_executions=true` on at least one trade holding the contract and verify `GET /api/v1/trades?has_unlinked_executions=true` returns it
- [x] 8.5 Frontend trading overview: add/verify a system filter "Needs linking" wired to `has_unlinked_executions=true`

## 9. Spec, docs and verification

- [x] 9.1 Apply the deltas in `specs/execution-overwrite-protection/spec.md` to `openspec/specs/execution-overwrite-protection/spec.md`
- [x] 9.2 Run `ruff check`, `ruff format`, `mypy --strict` (lint-check skill)
- [x] 9.3 Run the full backend test suite (unit-test skill)
- [x] 9.4 End-to-end verification against the real Schwab payload: import once, confirm both stuck positions close, import again, confirm the second run is a clean no-op
- [x] 9.5 Update `CHANGELOG.md` — call out that previously stuck positions will close on the next import, shifting historical metrics and the equity curve
- [x] 9.6 Decide whether the import dialog needs to surface warnings more prominently (design.md Open Question 5); raise a separate frontend change if so
- [x] 9.7 Add a zero-insert self-heal trigger: when an open protected trade has an absorbable unlinked execution on the same contract, force projection rebuild even with `inserted_raw_ids=0`
- [x] 9.8 Guard the self-heal trigger to Schwab imports and exclude unresolved manual-standin contracts so ordinary zero-insert imports remain fast no-ops

## 10. TradeChart open_close and option-line behavior

- [x] 10.1 Spec: record that TradeChart execution classification prioritizes `open_close` (`O`/`C`) and falls back to direction only when absent
- [x] 10.2 Spec: record that generic entry/exit price lines are suppressed for option trades (trade-level option or option legs present)
- [x] 10.3 Confirm implementation already matches this behavior in `frontend/components/charts/TradeChart.tsx`
