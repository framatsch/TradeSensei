## Why

The `execution-overwrite-protection` change shipped a `user_modified` gate and a trade-level `is_manually_edited` skip, but two real data-loss paths remain open. First, `TradeService.update_trade` writes user metadata (`journal`, `user_rating`, `image_urls`, `tradingview_link`, `playbook_id`) **without** marking any protection — so trades whose only user contribution is a journal entry or screenshot are silently deleted and rebuilt from pristine executions on the next broker re-import. Second, trades edited **before** the protection code shipped carry `is_manually_edited=False` and `user_modified=False` legs; the rebuild deletes them and re-materialises them from the untouched base layer, destroying all attached metadata. A confirmed production incident lost journals and screenshots exactly this way.

## What Changes

- Add an **Alembic data-migration** that backfills protection for legacy edited trades: set `is_manually_edited=True` on every trade carrying any metadata signal (journal, rating, screenshots, tradingview link, playbook, notes, tags, or annotations), set `user_modified=True` on all of those trades' non-deleted executions, and set `user_modified=True` on `imported` executions whose `price`/`quantity`/`commission` diverge from their linked `BrokerRawTransaction`.
- Extend `PATCH /api/v1/trades/{id}` so that mutating any metadata field marks the trade `is_manually_edited=True` **and** flags its non-deleted executions `user_modified=True` (screenshot add/remove flow already routes through `update_trade`, so it is covered).
- Add an **import guard clause**: when a raw-pipeline import inserts zero new `BrokerRawTransaction` rows and `overwrite_manually_edited` is False, skip the split-child purge and full projection rebuild entirely.
- Fix **PATCH symbol-change dual-scoping**: when `PATCH /api/v1/executions/{id}` changes an execution's `symbol`, re-aggregate both the old-symbol and new-symbol trade chains so the old FIFO chain is cleaned and the new one is built correctly.
- Add an `execution_state` query parameter to `GET /api/v1/trades` (values `manual`, `edited`, `imported`) that filters trades by the state of their linked executions via `EXISTS` subqueries, and surface a matching multi-select control in the trades-table filter panel (`TradeFilterBar`) with URL/saved-view round-tripping.

### Follow-up hardening (orphaned-execution defect)

A confirmed defect surfaced after the protection landed: the raw-pipeline rebuild's `manually_edited_keys` skip runs *before* the existing-trade lookup, so a metadata-protected trade **swallows** new broker executions instead of absorbing them — the incoming closing leg is never linked (`trade_id` stays `NULL`), the trade never closes, and the import reports `+0 created` with no warning (a real LOGI position is stuck open). The following are added to close this:

- **Reconcile-before-skip**: resolve the existing trade before honoring the protection skip and apply the metadata-safe structural update so new executions link onto the protected trade.
- **Stable UUID-anchor identity**: replace the brittle `(broker_conid, opened_at)` match-key (which `execution-overwrite-protection` D1 already flagged as fragile) with a trade's chronologically-first non-deleted execution as its durable cross-import identity; a rebuilt trade inherits the existing trade's `id` via its anchor.
- **Metadata carry-forward**: when a trade's prior anchor execution is removed, transfer its metadata to the next-oldest surviving execution's trade before the old trade is deleted.
- **Protection reporting**: `ImportResult` gains protected-reconciled/skipped counts and warnings so this class of issue is never silently invisible.
- **Reset-to-broker-state hard-delete**: an explicit hard-delete mode for `imported` executions that physically removes the leg and releases the linked `BrokerRawTransaction` re-import guard (`suppressed=False`), providing a supported repair path distinct from soft-delete.
- **Orphan-repair migration**: an idempotent data-only migration that links already-orphaned imported executions to their trade and recomputes close fields (repairs the LOGI incident).

Explicitly out of scope (deliberate): pauschal marking `split`/`merged`/`manual` executions (design-forbidden — see `execution-overwrite-protection` D1), the already-implemented `user_modified` gate in `delete_split_children_for_account`, and symbol-scoping the account-wide FIFO rebuild (`affected_symbols`) — the latter risks breaking multi-symbol combo positions and is deferred to a separate change.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `execution-overwrite-protection`: Broaden protection to cover column-level trade metadata (journal, rating, screenshots, tradingview link, playbook) at both the trade and execution level; add a legacy-backfill migration requirement; add an import guard clause for zero-insert imports; require dual-scope re-aggregation on execution symbol changes; add an execution-state trade filter. **Follow-up hardening**: require the import rebuild to reconcile (not skip) new executions onto metadata-protected trades; replace the brittle `(broker_conid, opened_at)` match-key with a stable UUID-anchor trade identity; carry metadata forward when an anchor execution is removed; report protection-driven skip/reconcile counts and warnings in import results; add a hard-delete "reset to broker state" for imported executions that releases the raw-transaction re-import guard; and repair already-orphaned imported executions via an idempotent data migration.

## Impact

- **Database**: one Alembic data-migration (no schema change — all target columns already exist). Backfills `trades.is_manually_edited` and `logical_executions.user_modified`.
- **Backend services**: `trade_service.py` (`update_trade` marks protection), `import_service.py` (zero-insert guard clause), `execution.py` (`update_execution` dual-scope re-aggregation).
- **Backend repositories / schemas**: `TradeFilterParams` gains `execution_state`; `trade_repository.py` list query gains `EXISTS`-based state filtering.
- **Backend API**: `GET /api/v1/trades` gains the `execution_state` query parameter; `PATCH /trades/{id}` and `PATCH /executions/{id}` keep their contracts (additive internal behaviour only).
- **Frontend**: a trade-table filter control for execution state in `TradeFilterBar`, wired through the `TradeFilters` type, the `useTrades` query hook, URL serialization (`tradeFilterUtils` / `useTradeFilterParams`), the active-filter count, and "Clear Filters"; client regenerated via `openapi-sync` after backend deploy. No breaking change; existing clients ignore the new parameter.
- **Tests**: migration backfill, `update_trade` protection marking, screenshot flow coverage, zero-insert guard, PATCH symbol-change re-aggregation, execution-state filter.
- **Follow-up hardening impact**: `import_service.py` (reconcile-before-skip, UUID-anchor resolution, metadata carry-forward, protection reporting); `execution.py` (`delete_execution` imported-leg hard-delete/reset with raw-transaction release); `trade_repository.py` / `broker_raw_transaction_repository.py` (anchor lookup, guard release); `ImportResult` schema (protected-reconciled/skipped counts + warnings); `DELETE /api/v1/executions/{id}` (opt-in reset mode); one idempotent Alembic orphan-repair data-migration. Tests: protected-trade reconciliation, anchor identity + carry-forward, protection reporting, imported-leg reset, orphan-repair migration.
