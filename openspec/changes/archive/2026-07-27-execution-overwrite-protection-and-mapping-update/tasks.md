## 1. Database Migration

- [x] 1.1 Create Alembic migration adding `trades.has_conflict` (`Boolean`, `nullable=False`, `server_default='false'`)
- [x] 1.2 Verify migration up/down runs cleanly against a seeded local database via the `db-migration` skill
- [x] 1.3 Update the SQLAlchemy `Trade` model in `backend/app/models/trade.py` with the new `has_conflict` field and a docstring linking to the `execution-overwrite-protection` spec

## 2. Backend — Model & Schema Updates

- [x] 2.1 Update `backend/app/models/logical_execution.py` docstring to reflect that `user_modified` is set for `imported | split | merged` origins (remove the "only imported" implication)
- [x] 2.2 Add `has_conflict: bool` to `TradeRead` in `backend/app/schemas/trade.py`; ensure it is NOT accepted in `TradeUpdate` (aggregated/derived semantics)
- [x] 2.3 Add `raw_transaction_id: str` request body schema and response schema for the manual-link endpoint in `backend/app/schemas/execution.py`

## 3. Backend — Execution Update Rules

- [x] 3.1 In `backend/app/services/execution.py::update_execution`, replace the `origin == EXECUTION_ORIGIN_IMPORTED` marker guard with a set check `origin in {imported, split, merged}` so PATCH marks all editable origins
- [x] 3.2 Guard against no-op patches: only set `user_modified=True` when `update_data` contains at least one mutating field
- [x] 3.3 Confirm `origin='manual'` PATCH path leaves `user_modified` unchanged (add explicit branch/comment)

## 4. Backend — Repository Protection Gate

- [x] 4.1 In `backend/app/repositories/execution.py::delete_split_children_for_account`, add a `WHERE user_modified = false` clause; add an `override: bool = False` parameter that bypasses the clause when true
- [x] 4.2 In `restore_split_parents_for_account`, add a NOT EXISTS subquery that skips parents whose surviving split children include any `user_modified=true` row; add the same `override` bypass parameter
- [x] 4.3 In `backend/app/repositories/trade_repository.py::delete_by_user_account`, add a NOT EXISTS subquery that skips trades whose only remaining legs are all `user_modified=true`; extend the existing `include_manually_edited` semantics to also cover the new protection when `override` is false
- [x] 4.4 Wire the `override` parameter through `backend/app/services/import_service.py` so it equals `overwrite_manually_edited` at all three call sites (`delete_split_children_for_account`, `restore_split_parents_for_account`, `delete_by_user_account`)

## 5. Backend — Manual-Link Endpoint

- [x] 5.1 Add `POST /portfolios/{portfolio_id}/executions/{execution_id}/link-broker-transaction` in `backend/app/api/v1/executions.py` with request body `{raw_transaction_id: str}`
- [x] 5.2 Implement `ExecutionService.link_broker_transaction(execution_id, raw_transaction_id, user_id, portfolio_id)`:
  - fetch execution, reject if `origin != 'manual'` → 409
  - fetch BRT, reject if cross-user → 404
  - reject if BRT already referenced by another `LogicalExecution.source_id` → 409
  - set `LogicalExecution.source_id = raw_transaction_id` and `BrokerRawTransaction.suppressed = true` atomically
  - emit audit event `execution.linked_to_broker_transaction` with safe metadata (execution_id, raw_transaction_id)
- [x] 5.3 Add repository helper `BrokerRawTransactionRepository.get_by_id_for_user` if not already available, to enforce ownership on lookup

## 6. Backend — Deletion Cascade for Linked Manual Executions

- [x] 6.1 In `backend/app/services/execution.py::delete_execution`, extend the `origin == 'manual'` branch:
  - read `execution.source_id` before delete
  - open a single database transaction / begin nested transaction that (a) sets `BrokerRawTransaction.suppressed = false` when `source_id` is not null, then (b) hard-deletes the manual execution
  - on any exception, roll back both operations
- [x] 6.2 Emit audit event `execution.deleted` with `released_source_id` metadata (safe: just the BRT id string)
- [x] 6.3 Cover the unlinked case (source_id is null): existing behaviour, no BRT update

## 7. Backend — Conflict Detection & Auto-Clear in FIFO Aggregator

- [x] 7.1 Extract a pure helper `detect_duplicate_pairs(legs) -> bool` that returns `True` iff at least one pair of legs on the same trade shares `symbol`, `executed_at` (equal to the second), `direction`, `quantity`, `price`, where one leg has `origin='imported'`, the other has `origin='manual'` with `source_id=NULL`
- [x] 7.2 In `backend/app/services/import_service.py`, add a post-aggregation pass over each `trades_with_sources` result that calls the helper and assigns `trade.has_conflict = detect_duplicate_pairs(trade.legs)` (authoritative recompute — always set, never merge)
- [x] 7.3 Wire the same recompute into every trade re-aggregation entry point (`_re_aggregate_trade` in `execution.py` and any callers in `import_service.py`) so that leg edits, leg deletes, and manual-link operations auto-clear the flag when the duplicate disappears
- [x] 7.4 Add a defensive guard: if `trade.legs` becomes empty during rebuild, `has_conflict` MUST be reset to `false` (empty trade cannot have a conflict)

## 8. Frontend — API Client Regeneration

- [x] 8.1 Run the `openapi-sync` skill to regenerate the TypeScript client with the new endpoint and `has_conflict` field
- [x] 8.2 Verify generated types compile with `rtk tsc` (frontend)

## 9. Frontend — Import Dialog Rename

- [x] 9.1 Locate the import dialog component (likely `frontend/src/components/import/`) and rename the `overwrite_manually_edited` checkbox label from "Overwrite manually edited trades" to "Overwrite user modifications"
- [x] 9.2 Update the help/tooltip text to explain that both manually edited trades AND user-modified execution legs will be replaced by broker data
- [x] 9.3 Update any i18n keys / snapshot tests referencing the old label

## 10. Frontend — Manual Execution Link UI

- [x] 10.1 In the execution editor for `origin='manual'` legs, add a "Link broker transaction" action (button or menu entry)
- [x] 10.2 Implement a broker-transaction picker dialog (list BRTs for the same account, filter by symbol match, allow ID search)
- [x] 10.3 Call `POST /executions/{id}/link-broker-transaction` on confirm; on 409 show the conflict reason inline
- [x] 10.4 Invalidate the execution list and trade detail queries on success

## 11. Frontend — Conflict Banner & Execution-Pair Highlight

- [x] 11.1 In the trade detail page, render a warning banner when `trade.has_conflict === true` with copy explaining that a manual leg may duplicate an imported leg and offering two suggested actions: "Delete the duplicate" or "Link the manual leg to the broker transaction"
- [x] 11.2 In the execution legs table on the same page, implement a client-side helper that identifies the duplicate pair by matching the five-field key (`symbol`, `executed_at` to the second, `direction`, `quantity`, `price`) across imported and unlinked manual legs
- [x] 11.3 Visually mark both identified legs in the executions table (e.g. a coloured row indicator and a small "conflict" chip) so the user immediately sees which two rows are the duplicate pair
- [x] 11.4 The banner is NOT independently dismissible — it is driven purely by the `trade.has_conflict` field and disappears automatically once the backend recomputes the flag to `false` (after leg deletion or manual-link, followed by re-aggregation and query invalidation)
- [x] 11.5 Invalidate the trade detail and executions queries after any mutation that could affect the flag (leg delete, leg edit, manual-link) so the UI reflects the recomputed state

## 12. Backend Tests — Unit

- [x] 12.1 `test_update_execution_marks_all_editable_origins` — PATCH on split and merged origins sets `user_modified=true`; manual origin does not
- [x] 12.2 `test_delete_split_children_skips_user_modified` — repo call leaves `user_modified=true` rows untouched
- [x] 12.3 `test_restore_split_parents_skips_when_child_protected` — parent stays `deleted=true` when a user-modified child exists
- [x] 12.4 `test_delete_by_user_account_preserves_user_modified_trades` — trade backed only by protected legs survives the rebuild
- [x] 12.5 `test_link_broker_transaction_happy_path` — link endpoint sets `source_id` and `suppressed=true` atomically
- [x] 12.6 `test_link_broker_transaction_rejects_non_manual` — 409 for imported/split/merged origins
- [x] 12.7 `test_link_broker_transaction_rejects_cross_user` — 404 for another user's BRT
- [x] 12.8 `test_link_broker_transaction_rejects_double_link` — 409 when BRT already linked
- [x] 12.9 `test_delete_manual_releases_linked_brt` — hard-delete of a linked manual sets `suppressed=false` on its BRT in the same transaction
- [x] 12.10 `test_delete_manual_rollback_preserves_state` — simulate exception mid-transaction; both rows unchanged
- [x] 12.11 `test_delete_manual_unlinked_unchanged` — unlinked manual delete does not touch any BRT
- [x] 12.12 `test_conflict_flag_set_on_unlinked_duplicate` — aggregator sets `has_conflict=true` when the five-field key matches
- [x] 12.13 `test_conflict_flag_not_set_on_linked_replacement` — linked manual leg is not treated as a duplicate
- [x] 12.14 `test_overwrite_flag_bypasses_protection_gate` — with `overwrite_manually_edited=true`, user-modified rows are deleted
- [x] 12.15 `test_conflict_flag_auto_clears_on_leg_deletion` — deleting one leg of the duplicate pair and re-aggregating flips `has_conflict` back to `false`
- [x] 12.16 `test_conflict_flag_auto_clears_on_manual_link` — linking the manual leg to the imported leg's BRT and re-aggregating flips `has_conflict` back to `false`
- [x] 12.17 `test_conflict_flag_reraises_on_new_duplicate` — after auto-clear, introducing a fresh duplicate on the next import re-raises the flag
- [x] 12.18 `test_link_broker_transaction_rejects_relink_with_409` — attempting to link a BRT that is already referenced by another `LogicalExecution.source_id` returns `409 Conflict` and does not mutate any row

## 13. Backend Tests — Integration

- [x] 13.1 End-to-end import test: import file A, edit a split leg, re-import overlapping file B, assert the edit survives and trade metadata is unchanged
- [x] 13.2 End-to-end manual-link test: import fill, delete the imported execution, create manual replacement, link to the original BRT, re-import overlapping file, assert no duplicate and manual leg intact
- [x] 13.3 End-to-end delete-cascade test: delete the linked manual from test 13.2, re-import the original file, assert a fresh imported leg materialises and takes over

## 14. Frontend Tests — Playwright E2E

- [x] 14.1 Create `frontend/tests/e2e/re-import-protection.spec.ts`: seed a trade with a user-modified split leg, trigger a re-import, verify the leg values and trade notes/tags are preserved
- [x] 14.2 Create `frontend/tests/e2e/pnl-conflict-banner.spec.ts`: seed a trade with a manual leg duplicating an imported leg, trigger the import, verify the `has_conflict` banner renders and deleting one leg clears it
- [x] 14.3 Add a Playwright test for the manual-link UI: link a manual to a BRT, verify the request payload and success toast

## 15. Documentation & Spec Sync

- [x] 15.1 Update `docs/api-usage.md` with the new link endpoint and the `has_conflict` field
- [x] 15.2 Update `AGENTS.md` iteration table if this change lands as its own iteration; otherwise cross-reference the spec
- [x] 15.3 Add a CHANGELOG entry under `[Unreleased]` describing the protection semantics and the deprecated junction requirement

## 16. Verification & Archive

- [x] 16.1 Run `openspec validate execution-overwrite-protection-and-mapping-update` — must be clean
- [x] 16.2 Run backend `unit-test` skill and confirm zero regressions
- [x] 16.3 Run frontend `rtk tsc` and `rtk lint` — both clean
- [x] 16.4 Run the full Playwright suite (`playwright-e2e`) locally against a fresh docker stack via `deploy-local` skill
- [x] 16.5 On merge, run the `openspec-archive-change` skill to move the change under `openspec/changes/archive/` with today's date prefix
