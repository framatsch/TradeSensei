## 1. Metadata mutation marks protection (backend service)

- [x] 1.1 In `backend/app/services/trade_service.py` `update_trade`, define the metadata column signal set `{"journal", "user_rating", "image_urls", "tradingview_link", "playbook_id"}` and detect intersection with `data.model_fields_set`.
- [x] 1.2 When a metadata field is present, set `Trade.is_manually_edited=True` (reuse `TradeRepository.mark_manually_edited` or set on the model) before commit.
- [x] 1.3 When a metadata field is present, set `user_modified=True` on all non-deleted executions of the trade (add a repository helper e.g. `ExecutionRepository.mark_user_modified_for_trade(trade_id)` using a single `UPDATE ... WHERE trade_id=:id AND deleted=false`).
- [x] 1.4 Verify the screenshot add/remove helpers (`trade_service.py:123`, `:181`) flow through `update_trade` and are therefore covered; add coverage if they bypass it.
- [x] 1.5 In `backend/app/services/trade_metadata_service.py` (tag/annotation assign/remove/update) and `backend/app/services/note_service.py` (note create/update/delete), add the same execution-level `user_modified=True` marking after the existing `mark_manually_edited` calls.

## 2. Legacy protection backfill migration (Alembic)

- [x] 2.1 Generate a new Alembic revision (data-only, no schema change) via the `db-migration` workflow.
- [x] 2.2 `UPDATE trades SET is_manually_edited=true` WHERE any metadata signal holds: `journal IS NOT NULL AND journal <> ''`, `user_rating IS NOT NULL`, `image_urls <> '[]'`, `tradingview_link IS NOT NULL`, `playbook_id IS NOT NULL`, or `EXISTS` in `trade_notes` / `trade_taxonomies` / `trade_annotations` by `trade_id`.
- [x] 2.3 `UPDATE logical_executions SET user_modified=true` for non-deleted legs whose `trade_id` is in the set of trades marked in 2.2.
- [x] 2.4 `UPDATE logical_executions SET user_modified=true` for `origin='imported'` legs whose `price`/`quantity`/`commission` diverge (Decimal tolerance) from their linked `BrokerRawTransaction` via `source_id`; do NOT compare `symbol`.
- [x] 2.5 Make the upgrade idempotent (re-runnable) and the downgrade a no-op with an explanatory comment (pre-migration state is unrecoverable).
- [x] 2.6 Add a `logger.info` summary of affected trade/execution counts for operator visibility.

## 3. Import guard clause on zero inserts

- [x] 3.1 In `backend/app/services/import_service.py`, after `inserted_raw_ids` is computed (line ~354), gate the split purge (`delete_split_children_for_account`), parent restore, and the projection rebuild block behind `if inserted_raw_ids or overwrite_manually_edited:`.
- [x] 3.2 Ensure the import still completes and returns `raw_transactions_created=0` on the skipped path (no exceptions, correct response payload).
- [x] 3.3 Confirm the override path (`overwrite_manually_edited=True`) still runs the rebuild on zero inserts.

## 4. Execution symbol-change dual-scope re-aggregation

- [x] 4.1 In `backend/app/services/execution.py` `update_execution`, read `old_symbol = execution.symbol` before applying `update_data`.
- [x] 4.2 After the update, if `symbol` changed, re-aggregate the leg's prior trade chain (old symbol) in addition to the current trade — mirroring the two-trade re-aggregation pattern in `reassign_execution` (`execution.py:794-803`).
- [x] 4.3 Leave the non-symbol-change path re-aggregating only the current trade (unchanged behaviour).

## 5. Trade list filter by execution state

- [x] 5.1 Add `execution_state: list[Literal["manual","edited","imported"]] | None = None` to `TradeFilterParams` in `backend/app/schemas/trade.py` with a field description.
- [x] 5.2 In `backend/app/repositories/trade_repository.py` list query, build one `EXISTS` subquery per requested state and combine with `OR`: `manual`→`origin='manual'`; `edited`→`user_modified=True`; `imported`→`origin='imported' AND user_modified=False`; each scoped to `trade_id==Trade.id AND deleted==false`.
- [x] 5.3 Wire the parameter through the `GET /api/v1/trades` route handler into `TradeFilterParams` (repeatable query param).
- [x] 5.4 Confirm omitting the parameter leaves the result unfiltered by execution state.

## 6. Trade table UI filter (frontend)

- [x] 6.1 Add `execution_state?: string[]` to the `TradeFilters` interface in `frontend/hooks/useTrades.ts` and pass it through to the `GET /api/v1/trades` call (omit when empty).
- [x] 6.2 Add a multi-select control (Manual / Edited / Imported) to `frontend/components/trades/TradeFilterBar.tsx` — mirror the Asset Class toggle-button pattern; include it in `EMPTY_FILTERS` and `countActiveFilters`.
- [x] 6.3 Serialize `execution_state` in `frontend/lib/tradeFilterUtils.ts` (write to URL) and parse it in `frontend/hooks/useTradeFilterParams.ts` (read from URL), so saved views and shareable links round-trip.
- [x] 6.4 Regenerate the API client via the `openapi-sync` skill and confirm `execution_state` is present in `types.gen.ts` / `sdk.gen.ts`.
- [x] 6.5 Verify the filter interacts correctly with saved views (`SaveFilterModal` / `useSavedTradeFilters`) — the value persists and restores.

## 7. Tests

- [x] 7.1 Unit: `update_trade` with journal/rating/screenshot/tradingview/playbook sets `is_manually_edited=true` and marks all non-deleted legs `user_modified=true`.
- [x] 7.2 Unit: tag/annotation/note mutations set execution `user_modified=true`.
- [x] 7.3 Migration test: legacy trades with each metadata signal are backfilled; clean imported trades are not; imported legs diverging from BRT are marked; symbol-only divergence is not.
- [x] 7.4 Integration: a metadata-protected trade survives a re-import with `overwrite_manually_edited=false`.
- [x] 7.5 Unit/integration: zero-insert import skips rebuild; override forces rebuild on zero inserts; non-zero inserts rebuild as before.
- [x] 7.6 Unit: PATCH symbol change re-aggregates both old and new trade chains.
- [x] 7.7 Unit/integration: `execution_state` filter for `manual`/`edited`/`imported` and OR semantics across multiple values.
- [x] 7.8 Frontend: `TradeFilterBar` renders the execution-state control, updates `TradeFilters`, contributes to the active-filter count, and round-trips through the URL serializers.

## 8. API docs and client sync

- [x] 8.1 Update FastAPI route annotations/docstrings for the `execution_state` query parameter on `GET /api/v1/trades`.
- [x] 8.2 Run the `openapi-sync` skill to regenerate the frontend TypeScript client.

## 9. Import skip-order bugfix (reconcile-before-skip)

- [x] 9.1 In `backend/app/services/import_service.py` raw-pipeline rebuild (~lines 503-508), resolve the existing trade for the aggregated position BEFORE the `manually_edited_keys` skip; only skip when no existing trade resolves.
- [x] 9.2 When an existing (protected or not) trade resolves, route it through the existing `model_dump(exclude_unset=True)` update path and set `trades_with_sources[i].created_trade` so `_backfill_execution_trade_links` links the new leg.
- [x] 9.3 Confirm metadata columns are never touched on the reconcile path (aggregator never sets them; verify `exclude_unset` excludes them) and add a guard/comment documenting the invariant.
- [x] 9.4 Verify no `origin='imported'`, `deleted=false`, `trade_id IS NULL` leg remains after a rebuild that reconciles a protected trade (integration assertion).
- [x] 9.5 Investigate the legacy (non-raw) pipeline branches (`import_service.py` ~601-750) for the same skip-without-linking pattern; fix only if confirmed vulnerable.

## 10. Stable UUID-anchor trade identity

- [x] 10.1 Add a helper to derive a trade's anchor execution (earliest non-deleted `executed_at`, tie-break by execution `id`) — repository or service level, batch-loadable by `trade_id`.
- [x] 10.2 Add anchor-based existing-trade resolution replacing the `(broker_conid, opened_at)` `existing_trades_by_key` lookup in the raw-pipeline rebuild; a rebuilt trade inherits the existing trade's `id` when their anchor execution matches.
- [x] 10.3 Replace/augment `manually_edited_keys` protection resolution to key off the anchor execution's trade rather than `(broker_conid, opened_at)`.
- [x] 10.4 Keep the change schema-free (derive the anchor; do NOT add `anchor_execution_id`) — leave a comment noting denormalization as a future option if profiling requires.

## 11. Metadata carry-forward when anchor is removed

- [x] 11.1 In the rebuild, detect when a protected trade's prior anchor execution is absent from the active set and identify the next-oldest surviving execution's rebuilt trade as the transfer target.
- [x] 11.2 Transfer metadata BEFORE `delete_by_user_account`: copy columns (`journal`, `user_rating`, `image_urls`, `tradingview_link`, `playbook_id`) and re-parent related rows (`trade_notes`, `trade_taxonomies`, `trade_annotations`) via `trade_id` update to the target trade.
- [x] 11.3 Ensure the transfer is idempotent within the transaction and cannot double-attach (re-parent, not copy, for related rows).

## 12. Import protection reporting

- [x] 12.1 Add `trades_protected_reconciled: int = 0` and `trades_protected_skipped: int = 0` to `ImportResult` in `backend/app/schemas/imports.py` with field descriptions.
- [x] 12.2 Increment the counters on the reconcile and defensive-skip paths in `import_service.py` and include them in the returned `ImportResult`.
- [x] 12.3 Append a human-readable warning (symbol + date) to `ImportResult.warnings` for each reconciled/skipped protected trade.

## 13. Hard-delete "reset to broker state" for imported legs

- [x] 13.1 Extend `DELETE /api/v1/executions/{id}` with an explicit reset intent (finalize query flag vs. sub-route per design D11/open question) in `backend/app/api/v1/executions.py`.
- [x] 13.2 In `backend/app/services/execution.py` `delete_execution`, add an imported-leg hard-delete branch: physical `DELETE` + `raw_transaction_repo.set_suppressed(source_id, False)` in the same transaction; re-aggregate or cascade-delete the parent trade as appropriate.
- [x] 13.3 Keep default (no reset intent) behaviour unchanged: soft-delete for imported/split/merged, hard-delete for manual.
- [x] 13.4 Emit an `execution.reset` (or reuse `execution.deleted` with metadata) audit event including `released_source_id`.
- [x] 13.5 Update FastAPI route annotations/response docs for the reset mode.

## 14. Orphan-repair data migration

- [x] 14.1 Generate a data-only Alembic revision via the `db-migration` workflow.
- [x] 14.2 Select orphans (`origin='imported'`, `deleted=false`, `trade_id IS NULL`); for each, match a unique open trade on `(user_id, account_id, symbol, complementary direction, quantity)`.
- [x] 14.3 On a unique match: set `trade_id`, then recompute the trade's `exit_price`, `closed_at`, `pnl`, `net_pnl`, `commission` from its complete leg set.
- [x] 14.4 On zero or multiple matches: skip and `logger.warning` the orphan (do not guess).
- [x] 14.5 Make the upgrade idempotent (already-linked legs untouched); downgrade is a no-op with an explanatory comment.
- [x] 14.6 Add a `logger.info` summary of repaired vs. skipped counts.

## 15. Tests (orphan-fix / anchor / reset)

- [x] 15.1 Integration: a metadata-protected open trade absorbs a new closing execution on re-import; leg is linked, trade closes, metadata unchanged.
- [x] 15.2 Integration: after any rebuild reconciling a protected trade, assert zero orphaned imported executions for the account.
- [x] 15.3 Unit: anchor derivation (earliest `executed_at`, id tie-break) and anchor-based identity inheritance across FIFO re-slicing / `opened_at` shift.
- [x] 15.4 Integration: metadata carry-forward when the prior anchor execution is removed — metadata lands on the next-oldest execution's trade, nothing lost.
- [x] 15.5 Unit: `ImportResult` protected-reconciled/skipped counts and warnings populated correctly.
- [x] 15.6 Integration: reset-to-broker-state hard-delete of an imported leg physically deletes it, sets `suppressed=false`, re-materialises on next import; default delete still soft-deletes.
- [x] 15.7 Migration test: unique-match orphan is linked and its trade closed; ambiguous/unmatched orphan is skipped and logged; migration is idempotent.

## 16. API docs and client sync (follow-up)

- [x] 16.1 Update FastAPI annotations/docstrings for the execution reset mode (`DELETE /api/v1/executions/{id}`) and the new `ImportResult` fields (`trades_protected_reconciled`, `trades_protected_skipped`).
- [x] 16.2 Run the `openapi-sync` skill to regenerate the frontend TypeScript client and confirm the reset parameter and new `ImportResult` fields are present in `types.gen.ts` / `sdk.gen.ts`.

## 17. Verification

- [x] 17.1 Run the `lint-check` skill (ruff + mypy --strict) — zero errors.
- [x] 17.2 Run the `unit-test` skill (pytest) — all new and existing tests pass.
- [x] 17.3 Verify frontend type-check/build passes (trades filter changes compile).
- [x] 17.4 Run `openspec validate execution-metadata-protection-hardening` and resolve any issues.
