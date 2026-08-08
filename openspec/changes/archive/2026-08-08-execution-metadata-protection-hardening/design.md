## Context

The `execution-overwrite-protection` change (archived 2026-07-27) introduced the `LogicalExecution.user_modified` gate, the `Trade.has_conflict` flag, and the symmetric manual-link/suppressed lifecycle. It correctly wired protection for executions edited via `PATCH /executions/{id}` and for trades protected by tags, annotations, and notes (which already call `TradeRepository.mark_manually_edited`).

Two gaps remain, one of which caused a confirmed production data-loss incident:

- **Column-level trade metadata is unprotected.** `TradeService.update_trade` (`backend/app/services/trade_service.py:419-481`) writes `journal`, `user_rating`, `image_urls`, `tradingview_link`, and `playbook_id` without setting `is_manually_edited` or `user_modified`. The screenshot add/remove helpers (`trade_service.py:123`, `:181`) also route through `update_trade`, so screenshots are unprotected too.
- **Legacy edited trades were never marked.** Any trade edited before this protection shipped has `is_manually_edited=false` and `user_modified=false` legs. On the next raw-pipeline import, `TradeRepository.delete_by_user_account` (`trade_repository.py:772-820`) deletes all `is_manually_edited=false` trades and the projection is rebuilt from pristine executions — destroying journals, screenshots, and ratings.

Two secondary defects are addressed opportunistically because they share the same code paths:

- The import rebuild always runs even when zero new raw rows were inserted (`import_service.py:354-554`), an unnecessary full-account churn.
- `ExecutionService.update_execution` (`execution.py:194-251`) re-aggregates only the current trade; a `symbol` change leaves the old FIFO chain uncleaned.

Task 4 adds an `execution_state` trade filter, following the established `EXISTS`-subquery pattern already used in `delete_by_user_account` (`trade_repository.py:809-819`).

## Goals / Non-Goals

**Goals:**
- Protect all user-supplied trade metadata (columns + related collections) at both the trade level (`is_manually_edited`) and execution level (`user_modified`).
- Retroactively protect legacy edited trades via a data-only Alembic migration.
- Backfill `user_modified` on `imported` executions that diverge from their broker raw transaction.
- Avoid unnecessary rebuilds when an import inserts zero new raw rows (with an explicit override escape hatch).
- Clean both FIFO chains when a PATCH changes an execution's symbol.
- Add an `execution_state` trade filter using `EXISTS` subqueries.

**Non-Goals:**
- Do NOT mark `split`, `merged`, or `manual` executions en masse (contradicts `execution-overwrite-protection` D1; `manual` is user-owned by construction; `merged` is never touched by the rebuild deletion path).
- Do NOT symbol-scope the account-wide FIFO rebuild (`affected_symbols` in `delete_split_children_for_account` / the projection rebuild). Multi-symbol combo positions make this a genuine architectural change; it is deferred to a separate change.
- Do NOT add a schema migration — every target column already exists.
- Do NOT change `has_conflict` semantics or the manual-link lifecycle.
- Do NOT attempt to recover metadata already lost in the prior incident (unrecoverable).

## Decisions

### D1. Dual-level protection: `is_manually_edited` AND `user_modified`
**Choice**: On any metadata mutation, set `Trade.is_manually_edited=True` and set `user_modified=True` on all of the trade's non-deleted executions.
**Alternatives considered**:
- Trade-level only. Rejected — the import skip via `manually_edited_keys` matches on `(broker_conid, opened_at)`, which is brittle: if FIFO re-slices the trade differently on re-import, the key no longer matches and protection is lost. The execution-level gate in `delete_by_user_account` (`has_unprotected_leg`) is keyed on the durable `trade_id`→leg relationship and is the stronger backstop.
- Execution-level only. Rejected — the trade-level skip is the primary, cheaper gate and is already wired into the import loop; keeping it avoids regressions.
**Rationale**: The two gates are additive and cover each other's failure modes (per D1 in the archived design). Belt and suspenders is warranted for a confirmed data-loss path.

### D2. Metadata signal set is explicit and centralized
**Choice**: The protected signals are exactly: columns `journal` (non-empty), `user_rating`, `image_urls` (≠ `[]`), `tradingview_link`, `playbook_id`; and related rows in `trade_notes`, `trade_taxonomies`, `trade_annotations`. `update_trade` marks protection when `data.model_fields_set` intersects the column set. The existing tag/annotation/note services already mark the trade; they are extended to also set execution `user_modified`.
**Alternatives considered**:
- Mark on every trade PATCH regardless of field. Rejected — patching `direction`/`multiplier` (re-aggregation fields) is not a metadata edit and should not freeze the trade against broker corrections.
**Rationale**: A precise, named signal set avoids over-protection while covering every real user-authored artifact.

### D3. Migration is data-only, idempotent, forward-fixing, no-op downgrade
**Choice**: A single Alembic revision runs bulk `UPDATE` statements. `is_manually_edited` backfill uses a `WHERE` with the metadata predicate (columns + `EXISTS` on the three child tables). Execution `user_modified` backfill updates non-deleted legs of the marked trades, plus imported legs diverging from their BRT. Downgrade does nothing.
**Alternatives considered**:
- Reversible downgrade that clears the backfilled flags. Rejected — the pre-migration boolean state is not recorded anywhere, so a downgrade cannot distinguish backfilled `True` from organically-set `True`; clearing would re-open the data-loss path.
- Python row-by-row loop. Rejected — set-based SQL `UPDATE ... WHERE EXISTS(...)` is faster and simpler for a one-shot backfill.
**Rationale**: Backfill is a one-way safety correction; a no-op downgrade is the honest and safe choice.

### D4. BRT divergence comparison ignores `symbol`, uses Decimal tolerance
**Choice**: For `imported` legs linked via `source_id`, compare `price`, `quantity`, `commission` against the BRT with a small Decimal tolerance (reuse the project's existing tolerance conventions, e.g. `Decimal("0.0000001")`). Do NOT compare `symbol`.
**Rationale**: Corporate-action remaps legitimately change `logical_executions.symbol` while the BRT retains the original ticker (`logical_execution.py:105-106`); treating that as an "edit" would false-positive on every split-adjusted instrument.

### D5. Guard clause respects the override flag
**Choice**: Skip split purge + parent restore + rebuild only when `len(inserted_raw_ids) == 0 AND not overwrite_manually_edited`. When `overwrite_manually_edited=True`, run the rebuild even on zero inserts.
**Alternatives considered**:
- Skip unconditionally on zero inserts. Rejected — the override is the documented "reset to pristine broker projection" escape hatch; a user toggling it expects a rebuild even if no new rows arrived.
**Rationale**: Preserves the single-toggle reset semantics from `execution-overwrite-protection` D6 while eliminating needless churn on the common re-upload case.

### D6. Symbol-change dual-scope via targeted re-aggregation, not a symbol-scoped rebuild
**Choice**: In `update_execution`, capture `old_symbol` before the update. After the update, re-aggregate the execution's current trade (new symbol). If the symbol changed, additionally re-aggregate any trade the execution previously belonged to under the old symbol. Because a single PATCH moves one leg (it does not re-run FIFO across the account), the "old chain" cleanup is the re-aggregation of the leg's prior trade; the new chain is the re-aggregation of its current trade.
**Alternatives considered**:
- Build a full `affected_symbols` scoped rebuild and invoke it from PATCH. Rejected — that is the deferred Task 3.1/3.2 architecture; overkill for a single-leg edit and entangled with combo handling.
**Rationale**: Targeted re-aggregation of the two affected trades achieves the spec's intent (old chain corrected, new chain rebuilt) without introducing a symbol-scoped rebuild engine. Note: `reassign_execution` already demonstrates the two-trade re-aggregation pattern (`execution.py:794-803`).

### D7. `execution_state` filter via OR-combined EXISTS subqueries
**Choice**: Add `execution_state: list[Literal["manual","edited","imported"]] | None` to `TradeFilterParams`. In the repo list query, build one `EXISTS(select LogicalExecution ... where trade_id==Trade.id and deleted==false and <state predicate>)` per requested value and combine them with `OR`. Predicates: `manual`→`origin='manual'`; `edited`→`user_modified=True`; `imported`→`origin='imported' AND user_modified=False`.
**Rationale**: Matches the existing `EXISTS` idiom in the same repository; OR semantics across states is the intuitive "any matching leg" behaviour. All predicate columns are indexed (`ix_le_trade_id_deleted`, `ix_le_origin`).

## Follow-up Decisions (orphaned-execution defect)

The decisions above shipped the protection but introduced a regression: the raw-pipeline rebuild's `manually_edited_keys` skip (`import_service.py` ~503-508) executes a `continue` **before** the `existing_trades_by_key` lookup, so a metadata-protected trade never receives `created_trade`. `_backfill_execution_trade_links` (which skips sources where `created_trade is None`) then leaves the new leg unlinked (`trade_id=NULL`), the trade never closes, and the zero-insert guard (D5) masks the orphan permanently (`+0 created`). Root fragility: the `(broker_conid, opened_at)` identity, already flagged brittle in `execution-overwrite-protection` D1. The following decisions close this.

### D8. Reconcile-before-skip: resolve the existing trade before honoring the protection skip
**Choice**: In the raw-pipeline rebuild, resolve the existing DB trade for the aggregated position *first*. If one exists (protected or not), route it through the existing `model_dump(exclude_unset=True)` update path and set `created_trade` so the new leg links. Skip only when no existing trade resolves AND the key is protected.
**Alternatives considered**:
- Keep the skip; add a separate orphan-relink pass afterward. Rejected — two paths reconciling the same state invites drift; the existing update path already does exactly what's needed.
- Always overwrite protected trades. Rejected — violates the protection contract; only structural (non-metadata) fields may change.
**Rationale**: The metadata-safe update path already exists and runs for non-protected trades; the bug is purely ordering. Reuse is the minimal correct fix. Metadata columns are never touched because the FIFO aggregator never populates them and `exclude_unset` excludes them.

### D9. Stable UUID anchor = chronologically-first non-deleted `LogicalExecution`
**Choice**: A trade's durable cross-import identity is the `id` of its earliest (`min(executed_at)`, tie-broken by execution `id`) non-deleted execution. On rebuild, each newly-computed trade resolves its anchor execution's current DB `trade_id`; if that maps to an existing trade, the new trade inherits that `trade_id`. Anchor-based resolution replaces `(broker_conid, opened_at)` in both `existing_trades_by_key` and `manually_edited_keys` resolution.
**Alternatives considered**:
- Keep `(broker_conid, opened_at)`. Rejected — the root fragility; breaks on FIFO re-slice, partial-close splits, and corporate-action timestamp/symbol shifts.
- Add a persistent `trade.anchor_execution_id` column. Rejected for now — derivable from existing data; avoids a schema migration. Revisit only if profiling shows a hotspot.
**Rationale**: The leg→trade relationship is durable across re-aggregation; anchoring identity on it is the "stronger backstop" D1 named.

### D10. Metadata carry-forward when the anchor is gone
**Choice**: If a rebuilt trade's prior anchor execution is absent from the active set, transfer the old trade's metadata (columns `journal`, `user_rating`, `image_urls`, `tradingview_link`, `playbook_id`, and re-parent `trade_notes`/`trade_taxonomies`/`trade_annotations` via `trade_id` update) to the trade now anchored by the next-oldest surviving execution — **before** `delete_by_user_account` deletes the old trade.
**Alternatives considered**:
- Let the old trade (and its cascaded metadata) be deleted. Rejected — reintroduces the original data-loss class.
- Block the rebuild when an anchor is missing. Rejected — too coarse; halts legitimate imports.
**Rationale**: Metadata must follow the surviving execution history, not a specific (possibly-removed) leg. Re-parenting (not copying) prevents double-attachment.

### D11. Hard-delete "reset to broker state" for imported legs
**Choice**: Extend `DELETE /api/v1/executions/{id}` with an explicit reset intent (query flag or sub-route — finalized in tasks). For `origin='imported'` legs, reset performs a physical `DELETE` and, in the same transaction, sets the linked `BrokerRawTransaction.suppressed=False` so the leg re-materialises unmodified on the next import. Absent the reset intent, current soft-delete behaviour is unchanged. `manual` legs keep their existing hard-delete+release behaviour.
**Alternatives considered**:
- Only soft-delete imported legs (status quo). Rejected — soft-delete permanently blocks re-import (deliberate-removal semantics), so there is no supported "give me the broker version back" path; that is exactly the LOGI trap.
- A separate `/reset` endpoint. Acceptable; semantics identical, only routing differs.
**Rationale**: Gives users and repair tooling a clean, atomic reset that cooperates with the import guard instead of fighting it.

### D12. Import protection reporting is additive on `ImportResult`
**Choice**: Add `trades_protected_reconciled` and `trades_protected_skipped` plus targeted warnings (symbol + date). Existing fields unchanged; additions defaulted so no client breaks.
**Rationale**: The bug was invisible because these counts were internal-only. Surfacing them makes any future protection edge case diagnosable, not silent.

### D13. LOGI repair as an idempotent, orphan-scoped data-migration
**Choice**: A data-only Alembic migration selects `imported` executions with `trade_id IS NULL AND deleted=false`, resolves the owning trade by matching the closing leg to a unique open trade on `(user_id, account_id, symbol, complementary direction, quantity)`, links `trade_id`, and recomputes the trade's close fields. On zero or multiple matches, skip and log. Re-runnable; downgrade is a no-op.
**Alternatives considered**:
- One-off script outside Alembic. Rejected — a migration is version-controlled, runs in deploy, and is idempotent.
- Rely solely on the D8 code fix + a manual re-import. Rejected as the sole mechanism — the already-persisted raw row means a plain re-import hits the zero-insert guard, so the code fix alone won't retro-link the existing orphan. The migration guarantees the historical record is fixed.
**Rationale**: Deterministic, auditable repair of existing bad state, decoupled from whether/when the user re-imports.

## Risks / Trade-offs

- **[Risk] `update_trade` over-marks when a metadata field is present but unchanged (same value re-sent).** → Mitigation: acceptable — marking is idempotent and conservative; a client re-sending the same journal still expresses intent to keep it. Optionally compare against current value, but not required for correctness.
- **[Risk] Migration touches many rows on large accounts.** → Mitigation: set-based `UPDATE` with indexed predicates; runs once at deploy. No hypertable concerns (`trades`, `logical_executions` are regular tables).
- **[Risk] Guard clause skips rebuild but a prior partial import left inconsistent state.** → Mitigation: the guard only skips when zero new rows were inserted; any real change (which requires an insert) still triggers the rebuild. Execution edits re-aggregate synchronously in `ExecutionService`, independent of import.
- **[Risk] Symbol-change re-aggregation misses a chain if the old trade was already emptied.** → Mitigation: re-aggregation of a now-empty trade is a no-op/cleanup; the existing `reassign_execution` path already handles the empty-source-trade case and can be mirrored.
- **[Trade-off] Deferring symbol-scoped rebuild leaves the full-account rebuild in place.** → Accepted — correctness is unaffected; only performance. Combo-safety makes the scoped rebuild a separate, carefully-designed change.
- **[Risk] `execution_state` combined with existing filters could be slow on large trade sets.** → Mitigation: EXISTS subqueries short-circuit and use `ix_le_trade_id_deleted`; consistent with existing filter performance.
- **[Risk] Anchor derivation (`min(executed_at)`) is ambiguous for simultaneous fills.** → Mitigation: deterministic tie-break by execution `id`; identity only needs to be stable, not semantically "first".
- **[Risk] Deriving the anchor per rebuilt trade adds queries on large accounts.** → Mitigation: batch-load legs by `trade_id` (already done for backfill) and resolve anchors in memory; add a persistent `anchor_execution_id` column later only if profiling demands it.
- **[Risk] Carry-forward (D10) could double-attach metadata if old and new trades briefly coexist.** → Mitigation: transfer inside the rebuild transaction, before `delete_by_user_account`; re-parent related rows by `trade_id` update (not copy).
- **[Risk] Reset (D11) on an imported leg the user genuinely wanted gone.** → Mitigation: reset is explicit intent (flag/route), never the default; default DELETE still soft-deletes. Audit-log the reset with `released_source_id`.
- **[Risk] Orphan-repair migration (D13) mis-links to the wrong trade.** → Mitigation: match on the full `(user, account, symbol, complementary direction, quantity)` tuple against *open* trades only; on 0 or >1 candidates, skip and log rather than guess.
- **[Note] The follow-up keeps three protection mechanisms in place** (anchor identity + `is_manually_edited` + `user_modified`). → Accepted for now: the anchor replaces the *weak* key gate; consolidating the remaining gates is a separate, riskier refactor and is intentionally not attempted here (surgical scope).

## Migration Plan

1. **Backend deploy** — ships the code changes (`update_trade` marking, guard clause, symbol dual-scope, `execution_state` filter) and the Alembic data-migration.
2. **Migration execution** — Alembic upgrade runs the backfill `UPDATE`s. Idempotent; safe to re-run.
3. **Backwards compatibility** — all API changes are additive: `PATCH /trades/{id}` and `PATCH /executions/{id}` keep their contracts (internal marking only); `GET /trades` gains an optional `execution_state` parameter that existing clients omit.
4. **Frontend client regeneration** — run the `openapi-sync` skill so the generated client picks up the `execution_state` parameter. A UI filter control is optional and can follow.
5. **Rollback** — revert code first (new marking behaviour becomes inert; guard clause and dual-scope disappear). The migration downgrade is a no-op by design (D3); leaving backfilled protection in place is safe and desirable.

### Follow-up hardening deploy steps

6. **Follow-up backend deploy** — ships the D8 reconcile-before-skip fix, D9 anchor identity, D10 carry-forward, D11 hard-delete/reset, and D12 reporting.
7. **Orphan-repair migration** — the D13 data-migration runs on upgrade; idempotent and safe to re-run. Fixes the LOGI record and any same-class orphan.
8. **Backwards compatibility** — `ImportResult` additions are defaulted; `DELETE /executions/{id}` reset is opt-in; existing contracts preserved. Regenerate the client via `openapi-sync`; a "Reset to Broker State" leg-editor control is an optional follow-up.
9. **Follow-up rollback** — revert code (new behaviour becomes inert). The D13 migration downgrade is a no-op by design (a correct link is not "undone").

## Open Questions

- Should `update_trade` compare each metadata field against its current value to avoid marking on a no-op re-send? Current decision (D2/risk): mark on presence in `model_fields_set`; refinement is optional and non-blocking.
- Should the migration also emit an audit/log summary of how many trades/executions were backfilled? Recommended as a `logger.info` line for operator visibility; not a spec requirement.
- D11 routing: reuse `DELETE /executions/{id}?reset=true` vs. a dedicated `POST /executions/{id}/reset`? Leaning to a query flag for contract minimalism; finalized in tasks.
- Should D9 persist `anchor_execution_id` now (denormalized) or stay derived? Default: derived; revisit on profiling.
- Should the D13 repair migration emit an audit event per repaired trade, or only a `logger.info` summary? Leaning summary + per-trade debug line.
