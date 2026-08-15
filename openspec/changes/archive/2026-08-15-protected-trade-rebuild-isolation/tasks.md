## 1. Schema and model

- [x] 1.1 Add `has_unlinked_executions` (boolean, not null, server default false) to the `Trade` ORM model in `backend/app/models/trade.py`
- [x] 1.2 Generate the Alembic revision adding `trades.has_unlinked_executions`; downgrade drops the column. No data backfill (see design D4 / Migration Plan step 1)
- [x] 1.3 Expose `has_unlinked_executions` on `TradeRead` in `backend/app/schemas/trade.py` with a field description
- [x] 1.4 Apply the migration locally and verify the column exists with the expected default

## 2. Protected-execution resolution (single source of truth)

- [x] 2.1 Add a repository method to `backend/app/repositories/trade_repository.py` returning protected trade IDs (`is_manually_edited=true`) for a user+account
- [x] 2.2 Add a repository method to `backend/app/repositories/execution.py` returning non-deleted execution IDs and their `(symbol, conid)` pairs for a given set of trade IDs
- [x] 2.3 In `ImportService`, resolve the protected trade IDs, their execution IDs, and their held `(symbol, conid)` set **once**, immediately before `_collect_trade_creates_from_logical_batches` (design D8), and thread the result through the rebuild

## 3. Rebuild isolation

- [x] 3.1 Exclude protected executions from the aggregation input in `_iter_trade_creates_from_logical_batches` / `_collect_trade_creates_from_logical_batches`
- [x] 3.2 Exclude protected trades' legs from `_build_seed_combo_execution_trades` so a protected open combo is not re-seeded into the rebuild
- [x] 3.3 Remove the D8 reconcile branch for protected trades in `import_service.py` (~lines 556-604): a resolved protected trade is skipped and counted, never updated
- [x] 3.4 Filter protected execution IDs out of `direct_pairs` and `split_inputs` in `_backfill_execution_trade_links` so a protected trade's legs are never reassigned (design D2)
- [x] 3.5 Verify `delete_by_user_account` still preserves protected trades unchanged (no code change expected — confirm by test)

## 4. Orphan-lot suppression

- [x] 4.1 Thread the protected `(symbol, conid)` set into `aggregate_executions_fifo_with_sources` in `backend/app/utils/parsers/aggregator.py`
- [x] 4.2 Suppress sentinel orphan lot creation (`entry_price = Decimal("0.001")`, `aggregator.py:694` and `aggregator.py:818`) when the closing execution's `(symbol, conid)` belongs to a protected trade; emit a warning instead
- [x] 4.3 Confirm orphan-lot creation is unchanged for all other unmatched closing executions

## 5. Reporting and flagging

- [x] 5.1 Add an unlinked-execution count field to `ImportResult` in `backend/app/schemas/imports.py` with a default so existing clients are unaffected
- [x] 5.2 Emit a per-occurrence warning (symbol + execution date) into `ImportResult.warnings` and a matching `logger.warning` record for every execution left unlinked due to protection
- [x] 5.3 Set `has_unlinked_executions=true` on the protected trade associated with each unlinked execution during import
- [x] 5.4 Clear `has_unlinked_executions` in `ExecutionService._re_aggregate_trade` when no unlinked executions remain for the trade, alongside the existing authoritative `has_conflict` recompute

## 6. Merge protection and combo derivation

- [x] 6.1 In `TradeService.merge_trades`, set `survivor.is_manually_edited = True` after execution reassignment
- [x] 6.2 In `TradeService.merge_trades`, set `user_modified = True` on all non-deleted executions linked to the survivor
- [x] 6.3 In `TradeService.merge_trades`, set `is_combo = True` when the survivor's non-deleted executions span ≥2 distinct `conid`, **before** `_re_aggregate_trade(survivor.id)` is called
- [x] 6.4 Relax the merge validation (`trade_service.py:813-818`) so differing `asset_class` is permitted when the merge result qualifies as a combo; keep `symbol` and `account_id` matching required
- [x] 6.5 In `ExecutionService.merge_executions`, set `user_modified = True` on the created merged execution and `is_manually_edited = True` on its trade

## 7. Trade list filter

- [x] 7.1 Add an optional `has_unlinked_executions` filter field to `TradeFilterParams` in `backend/app/schemas/trade.py`
- [x] 7.2 Apply the filter as a column predicate in the `TradeRepository` list query
- [x] 7.3 Add the `GET /api/v1/trades` query parameter with an OpenAPI description
- [x] 7.4 Regenerate the frontend client via the `openapi-sync` skill
- [x] 7.5 Extend the frontend `TradeFilters` type and `EMPTY_FILTERS` (`TradeFilterBar.tsx:102`)
- [x] 7.6 Include the filter in the active-filter count (`TradeFilterBar.tsx:81`) and "Clear Filters"
- [x] 7.7 Add URL serialization in `lib/tradeFilterUtils.ts` and deserialization in `hooks/useTradeFilterParams.ts`
- [x] 7.8 Add the filter toggle control to `TradeFilterBar.tsx` following the `execution_state` control pattern
- [x] 7.9 Surface a notice on the trade detail page when `has_unlinked_executions` is true, visually distinct from the existing `ConflictBanner`

## 8. Backend tests

- [x] 8.1 Protected closed trade retains `closed_at`, `pnl`, `net_pnl` and all linked executions across a raw-pipeline re-import (reproduces the `8436a93e` incident)
- [x] 8.2 Protected trade's executions never appear in the aggregation input
- [x] 8.3 Backfill discards an assignment that would move an execution off a protected trade
- [x] 8.4 New closing execution for a protected trade stays unlinked, sets `has_unlinked_executions`, and is reported in `ImportResult.warnings` plus the count
- [x] 8.5 No sentinel orphan trade (`entry_price = 0.001`) is created for a protected contract
- [x] 8.6 Orphan lots are still created for unmatched closing executions on non-protected contracts
- [x] 8.7 Protected and non-protected trades on the same symbol coexist correctly through a rebuild (design Risks)
- [x] 8.8 `merge_trades` sets `is_manually_edited` and `user_modified` on all survivor legs
- [x] 8.9 `merge_trades` of two option trades with distinct `conid` sets `is_combo=true` and aggregates via the combo branch (`entry_price`/`exit_price`/`quantity` unset, `pnl` summed from closing legs)
- [x] 8.10 `merge_trades` of trades on a single `conid` keeps `is_combo=false`
- [x] 8.11 `merge_trades` permits differing `asset_class` when the result is a combo, still rejects mismatched `symbol`/`account_id`
- [x] 8.12 A merged trade survives a subsequent import with identity, structure, and legs intact
- [x] 8.13 `merge_executions` sets `user_modified` on the merged leg and `is_manually_edited` on its trade
- [x] 8.14 `has_unlinked_executions` clears on re-aggregation once no unlinked executions remain
- [x] 8.15 Trade list filter returns only flagged trades; omitting the parameter reproduces prior behaviour

## 9. Frontend tests

- [x] 9.1 Filter control round-trips through the URL and contributes to the active-filter count
- [x] 9.2 A saved view stored without the new key loads with the filter inactive
- [x] 9.3 Trade detail page renders the unlinked-executions notice only when the flag is true

## 10. Documentation and archive hygiene

- [x] 10.1 Add a superseded notice to D8 and D9 in `openspec/changes/archive/2026-08-08-execution-metadata-protection-hardening/design.md` pointing at this change, stating that reconcile-before-skip caused data loss and is replaced by isolation
- [x] 10.2 Update `docs/api-usage.md` with the new filter parameter and the `has_unlinked_executions` field
- [x] 10.3 Append the change to the `[Unreleased]` section of `CHANGELOG.md`

## 11. Verification

- [x] 11.1 Run the `lint-check` skill (ruff + `mypy --strict`) with zero errors *(blocked: existing unrelated lint/type issues in repo)*
- [x] 11.2 Run the `unit-test` skill and confirm all backend tests pass
- [x] 11.3 Run the frontend test suite
- [x] 11.4 Verify against a restored backup that a re-import leaves a merged/protected combo trade byte-identical in its structural fields and leg links
