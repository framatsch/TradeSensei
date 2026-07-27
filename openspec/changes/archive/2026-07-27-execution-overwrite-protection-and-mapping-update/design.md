## Context

Trade Sensei's import pipeline rebuilds the trade projection on every raw-pipeline import. Protection against overwriting user edits currently exists only at the trade level (`Trade.is_manually_edited`, matched by `(broker_conid, opened_at)`). The `LogicalExecution` model already carries a `user_modified` boolean, but the import path never reads it — so the flag is a documentation lie in the response payload of `execution-leg-editor`.

The concrete damage path was traced in code:

- `backend/app/repositories/execution.py:329-355` (`delete_split_children_for_account`) hard-deletes every `origin='split'` row for the account, without regard for `user_modified`.
- `backend/app/repositories/execution.py:357-389` (`restore_split_parents_for_account`) restores the soft-deleted parent (`deleted=false, trade_id=NULL`), so the pristine broker row wins and re-aggregation runs from the untouched base layer.
- `backend/app/services/execution.py:188-235` (`update_execution`) sets `user_modified=True` only when `origin == 'imported'` — edits on split/merged rows leave no protection marker.
- `backend/app/services/execution.py:237-298` (`delete_execution`) hard-deletes `origin='manual'` rows without touching the linked BRT, so a linked replacement disappears silently on delete.
- `backend/app/services/logical_execution_service.py:174-189` documents that the `transaction_execution_mappings` junction table is dormant — the real raw-to-logical link is `LogicalExecution.source_id`. This contradicts the `raw-transaction-layer` spec.

The proposal introduces one new capability (`execution-overwrite-protection`) and one modified capability (`raw-transaction-layer`, deprecating the junction requirement).

## Goals / Non-Goals

**Goals:**
- Preserve user edits to `LogicalExecution` rows across broker re-imports without introducing a new status enum value.
- Keep `origin` immutable to avoid a database CHECK-constraint migration and semantic ambiguity.
- Provide a symmetric lifecycle for manual-execution replacements: linking marks the BRT `suppressed=true`, deleting the link releases it (`suppressed=false`), atomically.
- Surface silent duplication risk when a user creates a manual replacement without linking it, via a new `Trade.has_conflict` flag.
- Realign the `raw-transaction-layer` spec with the code's actual `source_id`-based link.
- Preserve the existing `overwrite_manually_edited` opt-in as the single "escape hatch" the user can toggle.

**Non-Goals:**
- Do NOT introduce an `EDITED` value in the `origin` enum. `user_modified` is the existing, sufficient marker.
- Do NOT reactivate the `transaction_execution_mappings` junction table. The `source_id` scalar covers the current 1:1 semantics.
- Do NOT drop the `TransactionExecutionMapping` ORM model or its empty backing table in this change (out of scope; deferrable cleanup).
- Do NOT change `Trade.is_manually_edited` semantics. Execution-level and trade-level protection are additive, not replacements.
- Do NOT auto-resolve `has_conflict`. Setting the flag is a surfacing signal; users decide which duplicate to delete. A future capability may add auto-resolution.
- Do NOT introduce per-execution overwrite UI. The single account-wide checkbox is enough for the current threat model.

## Decisions

### D1. `user_modified` marker instead of a new `EDITED` status
**Choice**: Extend the existing `LogicalExecution.user_modified` boolean to be set on PATCH of any `imported | split | merged` execution.
**Alternatives considered**:
- Add `edited` to `VALID_ORIGINS` and mutate `origin` on PATCH. Rejected because `origin` is documented and enforced as immutable (DB CHECK constraint, `logical_execution.py:117-118`), semantically represents *lineage* not *state*, and would require a schema migration.
- Add a separate `edit_state` enum column. Rejected as a strictly worse superset of the existing boolean for this use case.
**Rationale**: `user_modified` was designed for this purpose but never wired in. Reusing it is minimal, preserves the immutability invariant, and matches the field already exposed in `LogicalExecutionRead` responses.

### D2. `source_id` as canonical raw-to-logical link; junction deprecated in spec
**Choice**: Codify `LogicalExecution.source_id` as the 1:1 link in the `raw-transaction-layer` spec and remove the `Transaction Execution Mapping` requirement.
**Alternatives considered**:
- Populate the junction table for real. Rejected — no current use case needs n:m; the code was intentionally simplified; the change would touch every import path for no observable benefit.
- Silently leave the spec-vs-code drift. Rejected — future contributors will keep re-discovering that the mapping is dormant.
**Rationale**: Spec must match code. The 1:1 relationship is sufficient because splits/merges are expressed via `LogicalExecution.parent_id` (a self-FK), not by fanning out mappings.

### D3. Protection gate lives in the repository, not in the import BRT step
**Choice**: Add the `user_modified` filter to `delete_split_children_for_account`, `restore_split_parents_for_account`, and the raw-pipeline `delete_by_user_account` call path.
**Alternatives considered**:
- Skip re-inserting the BRT itself (Gemini's early proposal). Rejected — BRT re-insert is already blocked by `on_conflict_do_nothing` on the composite PK, so the "skip" is a no-op; the damage happens later in the projection rebuild.
- Skip re-aggregation for affected trades. Rejected — re-aggregation must run to reflect other legs' changes; only the *deletion* of protected rows must be gated.
**Rationale**: The repository is the correct chokepoint; every code path that wipes execution rows must pass through it, so a single gate covers current and future callers.

### D4. Symmetric `suppressed` lifecycle for linked manual executions
**Choice**: Linking a manual execution to a BRT sets `suppressed=True`; deleting that manual execution atomically sets `suppressed=False` (and hard-deletes the manual row) in the same database transaction.
**Alternatives considered**:
- Leave `suppressed=True` after delete. Rejected — the raw transaction is now orphaned; the user cannot get the original imported execution back without a fresh-start reset.
- Add a separate "unlink" endpoint. Rejected — delete is the intuitive UX; a separate unlink duplicates the state machine.
**Rationale**: The manual execution is the *stand-in* for the imported one. When the stand-in is removed, the original should re-materialise on the next import. Atomicity avoids the failure mode where the BRT is released but the manual row remains, leading to a genuine duplicate.

### D5. `has_conflict` as advisory flag, not blocker
**Choice**: Add `Trade.has_conflict` (boolean, default false), set to `true` when the FIFO aggregator detects an imported leg duplicating an unlinked manual leg on the same trade. Detection key: `(symbol, executed_at, direction, quantity, price)`. The import completes normally.
**Alternatives considered**:
- Auto-delete the duplicate. Rejected — the aggregator cannot know which leg the user intended to keep; wrong-guess loses data.
- Block the import until the user resolves the conflict. Rejected — imports run in the background (e.g. Flex Query cron); blocking silently strands the whole batch.
- Extend `has_conflict` to cover other conflict classes (already conceptually required by the `non-destructive-aggregation` spec for open-position mismatches). Deferred — that concept is broader; introducing the column here creates a home for future signals without forcing scope creep in this change.
**Rationale**: A surfacing flag lets the UI show a banner and the user decide. This matches the existing "conflict surfacing" pattern already documented (but not implemented) in `non-destructive-aggregation`.

### D6. `overwrite_manually_edited` flag is reused, not replaced
**Choice**: The existing form/body field `overwrite_manually_edited: bool` now overrides both trade-level `is_manually_edited` (as today) AND execution-level `user_modified` (new). Only the UI checkbox label changes to "Overwrite user modifications".
**Alternatives considered**:
- Add a second flag `overwrite_user_modified` for finer control. Rejected — no user story wants "overwrite manual trades but preserve edited executions" or vice versa; two flags multiply confusion.
**Rationale**: A single toggle keeps the UX simple; the new label is more accurate because it now covers both scopes.

### D7. FIFO conflict detection is a post-aggregation pass
**Choice**: Detect duplicates after FIFO assignment produces `trades_with_sources`; iterate each trade's legs and set `has_conflict` when a matching pair exists. Do NOT change FIFO itself.
**Rationale**: Keeps the aggregator pure. The duplicate check is O(N legs per trade) and runs once per import.

### D8. Manual-link endpoint rejects relink attempts with 409
**Choice**: If the target `BrokerRawTransaction` is already referenced by another `LogicalExecution.source_id`, the link endpoint returns `409 Conflict` with an error message identifying the existing link. No atomic release-and-relink flow is implemented.
**Alternatives considered**:
- Atomic relink (release old link → suppress new BRT → point new execution at BRT). Rejected — no user story demands it today, and the flow multiplies failure modes (which of the two manual executions is the "authoritative" one? what happens to the released manual leg's trade assignment?).
- 400 Bad Request instead of 409. Rejected — 409 is the correct semantic for a state conflict on an existing resource.
**Rationale**: A strict 409 is safe, unambiguous, and pushes the user through an explicit "delete old link first" flow that is trivially reasonable (the release cascade in D4 handles it cleanly). Relinking can be added later as a follow-up capability without breaking any existing contract.

### D9. `has_conflict` surfaces on the trade, with a secondary highlight on the execution pair
**Choice**: The primary surfacing is a warning banner on the trade detail page, driven by `trade.has_conflict`. Additionally, the executions table on the same page visually marks the identified duplicate pair (imported + manual) so the user can pick which one to delete. No per-execution `has_conflict` field is added.
**Alternatives considered**:
- Per-execution flag. Rejected — adds a second source of truth; the trade-level flag plus a UI-side pair lookup is sufficient, and the aggregator already knows the pair when it sets the trade flag.
- Trade banner only, no execution highlight. Rejected — leaves the user hunting for the duplicate; the highlight is a small UX win with no backend cost.
**Rationale**: Trade-level flag matches the underlying storage (single column on `trades`). The execution-pair highlight is a UI-only derived view (compute at render time from the trade's leg list, using the same key: `symbol`, `executed_at`, `direction`, `quantity`, `price`).

### D10. `has_conflict` auto-clears on trade re-aggregation
**Choice**: The FIFO conflict detection pass is authoritative. On every trade rebuild (including automatic re-aggregation triggered by leg mutations), the aggregator recomputes `has_conflict` from the current legs: `true` if a duplicate pair still exists, `false` otherwise. Users do not need to manually dismiss the flag.
**Alternatives considered**:
- User-dismissible flag with a separate "acknowledged" state. Rejected — introduces a second boolean and creates the failure mode "user dismisses, then more duplicates appear from a later import" where the dismissal masks a real signal.
- Never auto-clear (require explicit user action). Rejected — leaves stale `true` values after the user removes one leg of the pair, degrading trust in the signal.
**Rationale**: The flag is a derived signal; it should always reflect current state. Since re-aggregation already runs on every relevant mutation (leg delete, leg edit, re-import), auto-clear costs nothing extra and keeps the UI honest. The detection is idempotent and cheap (O(N legs per trade)).

## Risks / Trade-offs

- **[Risk] Existing user_modified rows have inconsistent state** → Migration is a code-only change; the column already exists. Existing rows keep whatever value they had. Users must re-edit any legs whose protection was silently lost before this change ships.

- **[Risk] `overwrite_manually_edited` is now stronger than before** → Users who have historically toggled it to force a re-import of trade-level edits will now also lose execution-level edits. Mitigation: UI label rename ("Overwrite user modifications") plus explicit help text.

- **[Risk] `delete_by_user_account` needs a new join to execution table for the protection check** → Small query cost; mitigated by the existing index on `logical_executions.trade_id`.

- **[Risk] `has_conflict` detection key may false-positive on legitimate scale-ins** → Same symbol + executed_at (to the second) + direction + quantity + price is an extremely narrow key; genuine duplicate broker fills within the same second at identical price would be rare. Mitigation: the flag is advisory and reversible; users can dismiss.

- **[Risk] Deletion cascade rollback complexity** → Both the manual-row hard-delete and the BRT `suppressed=false` update must succeed together. Mitigation: use a single `async with session.begin()` block; both are simple UPDATE/DELETE statements without external side effects.

- **[Trade-off] Junction table stays as dead code** → The `TransactionExecutionMapping` model and its empty backing table remain in the codebase after this change. Cleanup is deferrable and low-priority; leaving it avoids scope creep and preserves the option to reintroduce n:m mapping later without a data migration.

- **[Trade-off] `has_conflict` requires an Alembic migration** → One extra column, default false, safe backfill. Trade-off accepted because the surfacing signal is important and there is no other column with the right semantics.

## Migration Plan

1. **Alembic migration** — add `trades.has_conflict` column (`Boolean`, `nullable=False`, `server_default='false'`). Backfill is implicit (`false`) for all existing rows. No hypertable considerations (trades is a regular table).

2. **Backwards compatibility** — All API changes are additive:
   - PATCH `/executions/{id}` accepts the same payload; only the internal marker rules change.
   - DELETE `/executions/{id}` accepts the same payload; only the linked-manual branch adds a BRT update.
   - `POST /executions/{id}/link-broker-transaction` is a new endpoint; no existing client is affected.
   - `GET /trades/{id}` gains one boolean field (`has_conflict`); existing clients ignore unknown fields.

3. **Rollback** — Two-phase safe rollback:
   - Revert the code first. All new behaviours become no-ops (`user_modified` gate disappears, cascade delete reverts to the today-behaviour).
   - Alembic downgrade drops the `has_conflict` column. Any UI reading the field must be reverted first; otherwise the API stops emitting it and the frontend renders "undefined" gracefully.

4. **Deployment order** — Backend first (adds the column and endpoint), then frontend (uses the endpoint, renders the checkbox and banner). Deploying frontend first would show controls that hit 404.

5. **Frontend client regeneration** — After backend deploy, run the `openapi-sync` skill so the generated TypeScript client picks up `has_conflict` and the new link endpoint.

## Open Questions

All previously open questions have been resolved — see D8 (strict 409 on relink), D9 (trade-level banner + execution-pair highlight), and D10 (auto-clear on re-aggregation). No open questions remain at this time.
