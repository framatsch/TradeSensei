## Why

The `execution-metadata-protection-hardening` change (archived 2026-08-08) introduced **D8 "reconcile-before-skip"**: on a raw-pipeline import, a metadata-protected trade resolved via its anchor execution is *always* reconciled rather than skipped, on the stated assumption that the structural update "never touches metadata columns" and is therefore safe. That assumption is wrong in one direction the design did not consider: it protects *metadata* columns, but leaves *structural* columns (`closed_at`, `pnl`, `net_pnl`) fully writable — and it does nothing at all to stop `_backfill_execution_trade_links` from re-assigning the protected trade's executions to freshly created trades.

A confirmed production incident proves the gap. Trade `8436a93e` (QQQ 735/743 call vertical, `is_combo=true`, `is_manually_edited=true`) was correctly closed with `pnl=-199.66` and four linked legs. Its two closing legs were executed as **separate single-contract orders two days apart**, so `build_combo_positions` — which only groups legs sharing one `broker_order_id` with ≥2 distinct `broker_conid` (`aggregator.py:187-205`) — cannot re-associate them on rebuild. On the next import the aggregator produced an opening-only combo, the D8 reconcile path overwrote `closed_at`/`pnl`/`net_pnl` with `NULL`, and the backfill re-linked both closing legs onto two new sentinel orphan trades (`entry_price=0.001`). The trade survived deletion because `is_manually_edited=true` — and was destroyed anyway. **Protection that only guards against `DELETE` is not protection.**

Two further gaps compound this: `TradeService.merge_trades` and `ExecutionService.merge_executions` — the exact user actions taken to repair such positions — set no protection marker at all and cannot set `is_combo`, so a manually merged multi-leg position is both unprotected and structurally mis-aggregated.

## What Changes

- **BREAKING (internal behaviour, supersedes D8/D9)**: metadata-protected trades (`is_manually_edited=true`) are **fully isolated** from the raw-pipeline projection rebuild instead of being reconciled. Their non-deleted executions are excluded from the FIFO/combo aggregation input, they are never reconciled, and their executions are never re-linked by the backfill. The archived `execution-metadata-protection-hardening` D8 (reconcile-before-skip) and the D9 anchor-identity resolution for protected trades are explicitly superseded.
- Broker executions that cannot be linked because their target trade is protected are left unlinked (`trade_id IS NULL`) and **reported**, never silently absorbed into a newly invented trade.
- **Orphan-lot suppression**: the FIFO aggregator's sentinel orphan trade (`entry_price = 0.001`) is not created for a `(symbol, conid)` that belongs to a protected trade — a direct consequence of removing protected legs from the aggregation input, which would otherwise leave later closing executions unmatched.
- New `Trade.has_unlinked_executions` boolean column, set during import when a protected trade could not absorb incoming executions, surfaced in the trade detail view and as an additive trade-list filter.
- `ImportResult` gains an unlinked-execution count plus per-occurrence warnings; every occurrence is also emitted via `logger.warning`.
- `TradeService.merge_trades` marks the survivor `is_manually_edited=true` and all its surviving legs `user_modified=true`, and sets `is_combo=true` when the merged legs span ≥2 distinct `conid` (with the symbol/account/asset-class validation relaxed accordingly) so `_re_aggregate_trade` uses the combo branch instead of computing a meaningless VWAP across different contracts.
- `ExecutionService.merge_executions` marks the resulting merged leg `user_modified=true` and its trade `is_manually_edited=true`.

Explicitly out of scope (deliberate): teaching `build_combo_positions` to match separately-closed combo legs across orders (high regression risk across all existing combo positions — the manual merge path is made durable instead); repairing already-corrupted data (a separate change, because it must be planned and validated against production); unifying `position_id` on merge (unclear impact, needs its own investigation).

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `execution-overwrite-protection`: Replace the D8 reconcile-before-skip behaviour with full rebuild isolation of metadata-protected trades (input exclusion, reconcile exclusion, backfill exclusion, orphan-lot suppression). Require unlinkable executions to be reported rather than absorbed. Require `merge_trades` and `merge_executions` to mark protection at both trade and execution level. Add the `has_unlinked_executions` trade flag, its import-time semantics, and an additive trade-list filter.
- `combo-positions`: Allow `merge_trades` to set `is_combo=true` when the merged execution set spans ≥2 distinct `conid`, and relax the merge validation so a combo may be formed from trades with differing `asset_class`.

## Impact

- **Database**: one Alembic schema migration adding `trades.has_unlinked_executions` (boolean, not null, default false). No data backfill.
- **Backend services**: `import_service.py` (protected-execution input exclusion, removal of the D8 reconcile branch, backfill guard, unlinked reporting, flag maintenance); `trade_service.py` (`merge_trades` protection marking + `is_combo` derivation + validation relaxation); `execution.py` (`merge_executions` protection marking).
- **Backend aggregation**: `utils/parsers/aggregator.py` — orphan-lot suppression for protected contracts.
- **Backend repositories / schemas**: `trade_repository.py` (protected-execution lookup, `has_unlinked_executions` filter via the established `EXISTS`/column-predicate idiom); `TradeFilterParams` gains an optional filter field; `ImportResult` gains an additive count field.
- **Backend API**: `GET /api/v1/trades` gains one optional query parameter; `TradeRead` gains one field. Both additive — existing clients are unaffected.
- **Frontend**: `has_unlinked_executions` badge/notice on the trade detail page, and a filter control in `TradeFilterBar` wired through `TradeFilters`, `EMPTY_FILTERS`, the active-filter count, and URL serialization (`tradeFilterUtils.ts` / `useTradeFilterParams.ts`) — following the `execution_state` precedent. Saved views store filters as JSONB, so existing views simply omit the key. Client regenerated via `openapi-sync`.
- **Documentation**: the archived `2026-08-08-execution-metadata-protection-hardening` design gains a superseded notice on D8/D9 pointing at this change, so the reversed decision is discoverable from the archive.
- **Tests**: protected-trade reimport invariance, unlinked-execution reporting, orphan-lot suppression, `merge_trades` protection + `is_combo` derivation, `merge_executions` protection, filter round-tripping.
