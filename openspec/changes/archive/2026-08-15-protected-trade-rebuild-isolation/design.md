## Context

### The incident

Trade `8436a93e-32d1-495d-aba0-fac3aad08c9e` (QQQ 735/743 call vertical, expiry 2026-08-07) was a correctly closed combo position: `is_combo=true`, `is_manually_edited=true`, `closed_at=2026-08-06`, `pnl=-199.66`, `net_pnl=-204.32`, with four linked `logical_executions` (two opens, two closes). After a raw-pipeline import on 2026-08-15 17:11:52 UTC the same row had `closed_at=NULL`, `pnl=NULL`, `net_pnl=NULL` and only its two opening legs. Both closing legs had been re-linked to two newly created trades — `3780c95a…` and `712c49a2…` — each carrying the FIFO aggregator's sentinel `entry_price = 0.001`.

The trade was protected and was destroyed anyway. That is the central fact this design responds to.

### Why the aggregator could not rebuild the position

`build_combo_positions` (`backend/app/utils/parsers/aggregator.py:187-205`) groups executions by `broker_order_id` and only treats a group as a combo when it contains **≥2 distinct `broker_conid`**. The DB shows why that fails here:

| Role | `broker_order_id` | distinct conids |
|---|---|---|
| Both opening legs | `0108f77d…6a434391.0001` | 2 → recognised as combo |
| 735C close (2026-08-04) | `0108f77d…6a7168a7.0001` | 1 → not a combo group |
| 743C close (2026-08-06) | `0197d6c9…6a740a22.0001` | 1 → not a combo group |

The legs were closed individually, two days apart, in separate single-contract orders. Each closing order therefore falls through to plain FIFO. Since the matching open lot was already consumed by the combo builder, FIFO has nothing to match against and emits a sentinel orphan lot (`aggregator.py:694`, `aggregator.py:818`). Only *open* combo positions are seeded across imports (`import_service.py:1722` `_build_seed_combo_execution_trades`); a closed one is never reconstructible.

This structural limitation predates the hardening change. On its own it is harmless: before D8, protected trades were skipped wholesale, so the incomplete rebuild result was simply discarded.

### Why the hardening change turned it into data loss

`execution-metadata-protection-hardening` D8 replaced the wholesale skip with an unconditional reconcile (`import_service.py:556-604`), justified as safe because:

> "Metadata columns are never touched because the FIFO aggregator never populates them and `exclude_unset` excludes them."

That is true and irrelevant. `PROTECTED_METADATA_COLUMNS` (`backend/app/core/constants.py:254`) contains exactly `{journal, user_rating, image_urls, tradingview_link, playbook_id}`. `closed_at`, `pnl`, and `net_pnl` are structural, are populated by the aggregator, and are therefore written. The runtime assertion at `import_service.py:580` guards only the metadata set and passed happily while the trade was reverted to open.

Two further gaps compound it:

- `_backfill_execution_trade_links` (`import_service.py:1159-1317`) contains **no protection check of any kind**. `bulk_update_trade_ids(direct_pairs)` reassigns `trade_id` unconditionally, which is the mechanism that moved the closing legs off the protected trade.
- `is_manually_edited` is consulted in exactly one place that matters: the `DELETE` guard in `TradeRepository.delete_by_user_account` (`trade_repository.py:844-845`). It has never gated updates or re-linking. The flag's name implies broad protection; its implementation only prevented deletion.

### Why the user's repair action was also unprotected

`TradeService.merge_trades` (`trade_service.py:780-867`) reassigns executions via `ExecutionRepository.reassign_to_trade` (`execution.py:294`), which writes `trade_id` and nothing else. It never calls `mark_manually_edited`, never sets `user_modified`, and cannot set `is_combo` — `is_combo=True` is assigned in exactly one place in the entire backend, `aggregator.py:334`. `ExecutionService.merge_executions` (`execution.py:705-808`) has the same omission. The trade in the incident was protected only incidentally, presumably via a later note/rating edit routed through `mark_manually_edited`.

### Data context for the decisions below

- 646 `broker_raw_transactions`, 0 `suppressed`, 0 rows containing `cancel`/`correct`/`amend` markers. Duplicate `(conid, executed_at)` groups are ordinary partial fills (up to 19 in one second), not corrections.
- IBKR delivers a correction as a **new** `tradeID`, and raw rows are keyed by a unique `source_id`. A correction therefore always arrives as a new execution, never as a mutation of an existing row.
- Currently corrupted state: 2 sentinel orphan trades, 1 affected combo.

## Goals / Non-Goals

**Goals:**

- Make `is_manually_edited` mean what its name implies: a protected trade is not deleted, not updated, and not stripped of its executions by the import rebuild.
- Ensure that when the importer cannot do the right thing, it does nothing visible-and-reported rather than something wrong-and-silent.
- Make the manual merge — the user's actual repair tool — durable across imports and structurally correct for multi-leg positions.
- Give the user a persistent, discoverable signal when executions could not be linked.

**Non-Goals:**

- Do NOT teach `build_combo_positions` to match separately-closed combo legs across orders. It would touch every combo position in the account (10 today, 8 of them currently correct) and carries the highest regression risk in this area. The manual merge path is made durable instead. Revisit as its own change if the manual workaround proves too costly.
- Do NOT repair already-corrupted data here. The repair must also run against production and deserves its own change with its own validation against real numbers.
- Do NOT change `has_conflict` semantics or reuse it as the unlinked-execution signal (see D4).
- Do NOT unify `position_id` on merge. The impact is unclear and it is unrelated to this defect.
- Do NOT address the fact that `merged` and `split` executions carry no `source_id` and are therefore permanently combo-blind (see Risks).

## Decisions

### D1. Isolation over reconciliation — supersedes archived D8

**Choice**: A trade with `is_manually_edited=true` is removed from the rebuild entirely. Its non-deleted executions are excluded from the aggregation input, no field update is applied to it, and its executions are never reassigned by backfill.

**Alternatives considered**:
- *Keep reconcile, extend the protected column set to include `closed_at`/`pnl`/`net_pnl`.* Rejected — it fixes the observed symptom while leaving the model wrong. The reconcile path would still apply a structurally incomplete aggregation result to a trade the aggregator demonstrably cannot reconstruct, and the backfill would still steal the executions. It also requires enumerating "structural fields that must not regress", a list with no natural boundary.
- *Reconcile only when the rebuilt position is not "worse" than the existing one (e.g. reject when a closed trade would become open).* Rejected as the primary mechanism — a heuristic comparison invites arguments about what counts as worse, and it still permits the backfill to move legs. It is, however, a reasonable belt-and-braces addition and is effectively subsumed: with the executions removed from the input, no competing position is produced at all.
- *Revert to the pre-D8 skip only.* Rejected — that is where the orphaned-execution defect D8 was written to fix comes from. Isolation keeps the skip but makes the consequence explicit and visible instead of silent.

**Rationale**: The aggregator's output is only authoritative for positions it can fully reconstruct. A protected trade is by definition one the user has asserted authority over. Feeding its legs back into an aggregation that may not be able to reproduce them, and then applying the result, inverts that authority. Removing the legs from the input makes every downstream stage correct by construction rather than by guard.

### D2. Input exclusion is the primary mechanism; reconcile and backfill guards are defence in depth

**Choice**: Implement all three — exclude protected executions from the aggregation input, remove the reconcile branch for protected trades, and filter protected executions out of `direct_pairs`/`split_inputs` in the backfill.

**Alternatives considered**:
- *Input exclusion alone.* Rejected — the input is assembled across several call sites (`_collect_trade_creates_from_logical_batches`, `_build_seed_combo_execution_trades`, ground-truth seeds). One missed path silently reopens the hole, and the failure mode is data loss.

**Rationale**: The incident is precisely a case where a single-layer guard (`PROTECTED_METADATA_COLUMNS` at `import_service.py:580`) was believed sufficient and was not. Each of the three layers fails independently; requiring all three to fail to lose data is proportionate to the consequence.

### D3. Orphan-lot suppression is a mandatory consequence, not an optional extra

**Choice**: Suppress the sentinel orphan lot (`entry_price = 0.001`) for a closing execution whose `(symbol, conid)` is held by a protected trade; leave the execution unlinked and report it. Orphan-lot creation is otherwise unchanged.

**Alternatives considered**:
- *Leave orphan-lot behaviour untouched.* Rejected — removing a protected trade's legs from the FIFO input means later executions on that contract have no open lot to match, so the aggregator manufactures exactly the sentinel trades this change exists to eliminate. Isolation without suppression relocates the bug rather than fixing it.
- *Suppress orphan lots globally.* Rejected — the sentinel serves a legitimate purpose for genuinely transferred-in positions with no import history. Narrow the suppression to contracts demonstrably owned by a protected trade.

**Rationale**: This is the one non-obvious consequence of D1 and the most likely source of a follow-up bug if left implicit. It is specified rather than discovered.

### D4. New `has_unlinked_executions` column rather than reusing `has_conflict`

**Choice**: Add `trades.has_unlinked_executions` (boolean, not null, default false), maintained during import and cleared on re-aggregation when no unlinked executions remain.

**Alternatives considered**:
- *Reuse `has_conflict`.* Rejected on three counts. (1) Semantics: `has_conflict` means "an imported leg and an unlinked manual leg on this trade describe the same fill" (`utils/conflict_detection.py:61-106`) — a duplication problem. Ours is the inverse, an execution that belongs to the trade but is not attached. (2) Persistence: `has_conflict` is recomputed authoritatively and unconditionally on every re-aggregation (`execution.py:998`, `import_service.py:641`), so a value set for a different reason is erased by the next leg edit. (3) UI: `ExecutionLegsTable.tsx:154-172` re-derives the five-field duplicate key client-side to highlight the offending rows; a flag set for another reason renders a `ConflictBanner` (`trades/[id]/page.tsx:407`) pointing at nothing.
- *No trade-level flag; rely on `ImportResult` warnings plus a query for `trade_id IS NULL`.* Rejected — the signal would exist only in the import response. Opening the affected trade later would show nothing wrong, which is the exact invisibility that let this incident run undetected.

**Rationale**: A distinct condition earns a distinct field. The cost is one additive schema migration with no backfill.

### D5. The trade-list filter follows the `execution_state` precedent exactly

**Choice**: Add one optional boolean to `TradeFilterParams`, a column predicate in the repository list query, and the corresponding frontend touchpoints: `TradeFilters` type, `EMPTY_FILTERS` (`TradeFilterBar.tsx:102`), active-filter count (`TradeFilterBar.tsx:81`), URL write (`tradeFilterUtils.ts:66-67`), URL read (`useTradeFilterParams.ts:28,46-52`), and a toggle control (`TradeFilterBar.tsx:617-640`).

**Rationale**: `execution_state` was added by the hardening change through exactly these seven touchpoints and is a working precedent. Saved views persist filters in `saved_trade_filters.definition` (JSONB), so pre-existing views simply lack the key and the filter reads as inactive. No breaking change on the API, the URL contract, or saved views.

### D6. Merge marks protection at both levels

**Choice**: `merge_trades` sets `survivor.is_manually_edited = True` and `user_modified = True` on every non-deleted execution linked to the survivor. `merge_executions` sets `user_modified = True` on the merged leg and `is_manually_edited = True` on its trade.

**Alternatives considered**:
- *Trade-level marking only.* Rejected — `delete_by_user_account` has a second, independent gate keyed on legs (`has_unprotected_leg`, `trade_repository.py:856-863`). Setting both means the two gates cover each other, consistent with the existing dual-gate design.

**Rationale**: A merge is an unambiguous assertion that the user's grouping beats the importer's. It is the single most explicit protection signal in the product and currently produces none.

### D7. Merge derives `is_combo` from distinct `conid` count

**Choice**: After reassignment and before re-aggregation, set `is_combo=True` when the survivor's non-deleted executions span ≥2 distinct `conid`. Relax the merge validation so differing `asset_class` is permitted in that case; `symbol` and `account_id` remain required to match.

**Alternatives considered**:
- *Require the user to declare combo intent explicitly in the merge request.* Rejected — additional API surface and a decision the data already answers unambiguously.
- *Leave `is_combo` alone.* Rejected — `_re_aggregate_trade` then takes the non-combo branch (`execution.py:1085`) and computes a volume-weighted average entry and exit across two different strikes. The resulting number is not wrong-but-approximate; it is meaningless. The existing validation at `trade_service.py:816` already anticipates mixed asset classes when either side is a combo, so the relaxation is consistent with intent.

**Rationale**: Distinct `conid` is precisely the signal the aggregator itself uses to identify a combo order (`aggregator.py:198`). Reusing it keeps one definition of "combo" in the system.

### D8. Ordering within the rebuild

**Choice**: Resolve protected trade IDs and their execution IDs once, immediately before `_collect_trade_creates_from_logical_batches`, and thread that set through aggregation-input assembly, the reconcile branch, the backfill filter, and the orphan-lot suppression check.

**Rationale**: A single authoritative snapshot avoids the class of ordering bug that produced the original defect, where the protection check ran before the trade lookup it depended on. One query, one set, consumed by four call sites.

## Risks / Trade-offs

- **[Risk] A protected trade genuinely needs a new broker execution and can no longer receive it automatically.** → Mitigation: this is the accepted trade-off of D1 and the reason D4 and the reporting requirement exist. The execution stays unlinked, the trade is flagged, and the user attaches it manually. Evidence supports the cost being low: 0 corrections in 646 raw transactions, and a correction arrives as a new row rather than a mutation regardless.
- **[Risk] `overwrite_manually_edited=True` remains the only reset path, and it is coarse.** → Mitigation: unchanged from current behaviour; the existing metadata carry-forward (archived D10) still applies on that path. A per-trade reset is a plausible follow-up but is not required to fix this defect.
- **[Risk] Removing protected legs from FIFO changes matching for other trades on the same symbol.** → Mitigation: this is exactly what D3 addresses for the closing-execution case. Tests must cover a symbol where a protected trade and an unprotected trade coexist.
- **[Risk] `has_unlinked_executions` goes stale if the clearing path is missed.** → Mitigation: clear it in the same re-aggregation path that authoritatively recomputes `has_conflict`, so both flags share one lifecycle. A stale `true` is a false alarm, not data loss.
- **[Risk] Marking every merge as protected freezes trades that later receive legitimate broker data.** → Mitigation: accepted, and it is the intended semantics — the user asserted authority. The flag plus the unlinked-execution report makes the situation visible rather than silent.
- **[Risk] `merged` and `split` executions carry no `source_id` (confirmed: 404 split children, 0 with `source_id`) and therefore never receive a `broker_order_id`, so they can never participate in combo grouping.** → Mitigation: out of scope, and largely neutralised by this change — such trades are protected after a merge and excluded from the rebuild, so their combo-blindness stops mattering. Documented so it is not rediscovered as a new bug. Note the related trap: `restore_split_parents_for_account` (`execution.py:505-507`) will not restore a parent whose surviving split child is `user_modified=true`, leaving that history permanently combo-blind.
- **[Trade-off] Not fixing `build_combo_positions` means separately-closed combo legs still require a manual merge.** → Accepted per the Non-Goals, on the user's explicit judgement that the regression risk to existing combos outweighs the convenience.
- **[Risk] The specification reverses a decision recorded in an archived change, which a future reader may not see.** → Mitigation: a superseded notice is added to `openspec/changes/archive/2026-08-08-execution-metadata-protection-hardening/design.md` on D8/D9 pointing at this change. Without it the archive still reads as current guidance, which is how this defect was introduced.

## Migration Plan

1. **Schema migration** — Alembic revision adding `trades.has_unlinked_executions` (boolean, not null, server default false). No data backfill; the flag is established on the next import.
2. **Backend deploy** — isolation, reporting, orphan-lot suppression, merge marking, and `is_combo` derivation ship together. Deploying isolation without orphan-lot suppression would actively create sentinel trades (D3), so they must not be split across releases.
3. **Client regeneration** — run the `openapi-sync` skill for the new `TradeRead` field, the `GET /trades` parameter, and the `ImportResult` count.
4. **Frontend deploy** — trade-detail notice and filter control.
5. **Data repair** — deliberately excluded; a separate change, planned against production once its scope is measured there.
6. **Rollback** — revert the backend and frontend; the added column is inert and may remain. The schema migration's downgrade drops the column and is safe because nothing else reads it.

## Open Questions

- Should the trade-detail notice offer a direct action ("attach outstanding executions") or only inform? Informing is sufficient for this change; an action is a natural follow-up once the flag exists and its real frequency is observable.
- Should `has_unlinked_executions` also be set when executions are unlinked for reasons unrelated to protection? Current scope is protection-driven only, to keep the signal precise. Broadening it is additive later.
- Is a per-trade "reset to broker state" needed as a companion to permanent merge protection, or is the account-wide `overwrite_manually_edited` acceptable? Deferred until the frequency of the need is known.
