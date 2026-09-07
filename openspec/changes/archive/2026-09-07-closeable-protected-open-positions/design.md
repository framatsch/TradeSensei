## Context

The raw-pipeline import rebuilds the entire trade projection for an account on every
run: it loads all `logical_executions` for the account, runs combo grouping and FIFO
aggregation over them, then deletes and recreates the resulting trade rows.

`execution-overwrite-protection` was introduced because that rebuild destroyed trades
the user had documented. The chosen mechanism was **isolation**: a protected trade's
executions are removed from the aggregation input, its contract is blacklisted against
sentinel-orphan creation, the trade row is exempted from deletion, and no field update
is applied to it.

Isolation solves deletion but forbids amendment. An open documented position can
therefore never receive its closing leg. See `proposal.md` for the full trace.

There is already a mechanism in the codebase for the exact opposite behaviour: open
COMBO positions must survive a rebuild *and* be closeable. They are handled by
`_build_seed_combo_execution_trades` (`import_service.py:1795`), which feeds their legs
back into aggregation carrying `db_trade_id`, plus the update path at
`import_service.py:740` ("Case 1: This result closes an existing open DB lot (UPDATE)")
and the `preserved_trade_ids` exclusion from `delete_by_user_account`. This design
generalises that mechanism.

### Empirical baseline

Both the production and the local dataset were measured before writing this design.

| Measure | Production | Local |
|---|---|---|
| executions with `origin='merged'` | 0 | 0 |
| `imported` executions with `user_modified=true` | 54 | 50 |
| …of those, bit-identical to their `broker_raw_transactions` row (`quantity`, `price`, `direction`, `executed_at`) | 54 (100 %) | 50 (100 %) |
| …of those, deviating from the raw row | 0 | 0 |
| `split` executions with `user_modified=true` | 9 | 9 |

Interpretation:

- `merge_executions` has never been used — there are no `merged` rows at all.
- No `imported` execution carries a value that differs from what the broker delivered,
  so no value-changing `PATCH /api/v1/executions/{id}` is present in either dataset.
- Split children are created without the marker (`execution.py:650-687`), so the 9
  marked ones (ATOS, META — both closed, protected trades) were also marked after the
  fact by a trade-level action.

**Every `user_modified=true` marker currently in existence is collateral from a
trade-level action**, not evidence of an execution edit. The paths that set it are
`NoteService`, `TradeMetadataService`, `TradeService.update` (`trade_service.py:599`)
and `TradeService.merge_trades` (`trade_service.py:864-865`).

This is a snapshot, not a guarantee about the future: the marker still has a legitimate
purpose for genuine execution edits, and the design keeps it.

### Relevant current call sites

| Location | Role today |
|---|---|
| `import_service.py:1695` `_resolve_protected_execution_snapshot` | builds `trade_ids`, `execution_ids`, `contracts` |
| `import_service.py:1777` | drops `execution_ids` from the aggregation input |
| `aggregator.py:683`, `aggregator.py:815` | drops closing executions for `protected_contracts` |
| `import_service.py:584-594` | skips field updates for protected trades |
| `import_service.py:699-706` | exempts protected trades from deletion |
| `import_service.py:660-679` | reports unlinked executions, sets `has_unlinked_executions` |
| `note_service.py:85-86`, `trade_metadata_service.py:77-159` | set both protection markers |

## Goals / Non-Goals

**Goals:**

- An open trade protected only by metadata can be closed by a subsequent import.
- An open trade whose legs the user has corrected (`user_modified=true`) can also be
  closed; the corrected values are what the match is computed against.
- User-supplied metadata is provably never written by an import, on any path.
- Closed protected trades keep today's behaviour exactly.
- No data migration.

**Non-Goals:**

- Changing how `overwrite_manually_edited=true` behaves.
- Changing combo handling.
- Repairing the executions already orphaned in production (tracked separately — see
  Migration Plan).

## Decisions

### D1 — Split the protection snapshot by trade state instead of relaxing it globally

`ProtectedExecutionSnapshot` currently mixes open and closed protected trades. It is
split into two sets keyed on `Trade.closed_at IS NULL`:

- **closed protected** → today's behaviour verbatim: executions excluded from
  aggregation input, contract in `protected_contracts`, trade skipped from updates.
- **open protected** → executions enter aggregation as seed lots; contract is *not* in
  `protected_contracts`; trade is eligible for aggregate-field updates.

*Alternative considered — drop the isolation entirely for all protected trades.*
Rejected: for a closed protected trade an incoming closing execution genuinely is a new
position (a later re-entry in the same instrument), and re-aggregating a closed
protected trade could restructure legs the user deliberately corrected. Keeping closed
trades isolated preserves the guarantee that a finished, documented trade never moves.

*Alternative considered — a post-aggregation reconciliation pass* that scans unlinked
closing executions and closes matching open protected trades directly. Rejected: it
would duplicate FIFO matching logic (partial closes, scale-outs, position flips, split
adjustments) outside the aggregator, which is exactly the class of parallel-pipeline
mistake AGENTS.md warns against.

### D2 — Seed lots reuse the COMBO carry-forward mechanism

The seed for an open protected trade is a `TradeCreate` built from the trade's
non-deleted legs with `db_trade_id` set to the trade id, mirroring
`_build_seed_combo_execution_trades`. Consequences that fall out for free:

- FIFO matches the incoming closing execution against it, including partial matches.
- `source_execution_id` on the seed points at the real `logical_execution`, so
  `_backfill_execution_trade_links` links the closing leg to the existing trade.
- The trade id flows through to the update path at `import_service.py:740`, so the
  existing row is updated rather than deleted and recreated — which is what preserves
  the metadata and the related rows.
- `preserved_trade_ids` / `exclude_trade_ids` keep the row out of
  `delete_by_user_account` regardless of outcome.

Seed values are read from `logical_executions`, not from the import file. A leg the user
corrected therefore contributes its corrected quantity and price to the match.

### D3 — Guard rails on seed lots

Three invariants must hold, enforced explicitly rather than emergently:

1. A seed lot that is never matched MUST NOT produce a trade row. `_finalize_open_lots`
   emits leftover open lots as trades; seeds must be recognised by their `db_trade_id`
   and either skipped or routed to the update path as a no-op.
2. A seeded execution's stored values MUST NOT be written back.
3. A seeded execution MUST NOT be reassigned to a different trade by backfill. The
   existing `protected_execution_ids` guard in `_backfill_execution_trade_links`
   (`import_service.py:633-637`) already does this and is kept for open protected trades
   too — it must permit *adding* the new closing leg while refusing to *move* the
   existing one.

Violating (1) is how a duplicate open position would be created, so it needs a direct
test, not just an integration test.

### D4 — Trade-level mutations stop setting `user_modified`

`NoteService`, `TradeMetadataService`, `TradeService.update` (`trade_service.py:599`)
and `TradeService.merge_trades` (`trade_service.py:864-865`) drop the
`mark_user_modified_for_trade()` call and keep `mark_manually_edited()`.

`merge_trades` is included deliberately. Merging two trades is a statement about trade
*grouping*, not about the executions' values — the legs keep exactly the values the
broker delivered. Marking them `user_modified` claims otherwise and, before this change,
was one of the triggers for the defect. The merged survivor stays protected from
deletion via `is_manually_edited`.

The marker is specified as "the user edited this execution"
(`specs/execution-overwrite-protection/spec.md:4-5`). A note is not an execution edit.
Setting it there widens protection from one trade to every contract that trade holds,
and — before this change — was the trigger for the whole defect.

No protection is lost. `delete_by_user_account` guards protected trades on two
independent conditions:

```python
stmt = stmt.where(Trade.is_manually_edited.is_(False))      # :849  still applies
stmt = stmt.where(~(has_any_leg & ~has_unprotected_leg))    # :867  no longer triggered by notes
```

Line 849 alone covers documented trades. Line 867 remains for genuinely user-edited
legs, which is its stated purpose.

### D5 — Clear the existing markers in a one-off data migration

Earlier drafts of this design argued for no migration, on the assumption that the
existing markers could not be reliably classified. The measurement in *Empirical
baseline* removes that assumption: in both datasets **every** `user_modified=true`
execution is either bit-identical to its broker raw transaction (54 / 50 rows) or a
split child that was never created with the marker (9 rows). There is nothing to
preserve.

The migration therefore sets `user_modified = false` for every execution that satisfies
both:

1. it is not `origin='manual'`, and
2. either its `source_id` resolves to a `broker_raw_transactions` row whose `quantity`,
   `price`, `direction` and `executed_at` all equal the execution's, or it has
   `origin='split'` and `parent_id IS NOT NULL`.

Any row not satisfying this is left untouched and logged. On the current data that set
is empty, so the migration is a no-op guard for environments this design has not seen.

`Trade.is_manually_edited` is **not** touched. Documented trades keep their deletion
protection.

*Why bother, if the markers become inert anyway?* One concrete side effect makes the
cleanup worthwhile: `delete_split_children_for_account` is specified to exclude
`user_modified=true` rows from the purge, and `restore_split_parents_for_account` will
not restore their parents (`specs/execution-overwrite-protection/spec.md:32`). The 9
falsely-marked split children on ATOS and META therefore freeze a split structure that
no import can ever rebuild. Clearing the markers restores normal rebuild behaviour for
those two trades.

*Alternative considered — add a `protection_reason` column and backfill it.* Rejected:
the column earns its keep only if future behaviour needs to branch on the reason, which
after this change it does not.

*Alternative considered — leave the markers in place.* Rejected on the split-purge side
effect above; also leaves the database asserting something untrue about the user's
edits.

### D6 — Explicit metadata-preservation guarantee

`TradeCreate` carries a `journal` field (`backend/app/schemas/trade.py:112`). The
update path applies

```python
update_data = trade_data.model_dump(exclude={...}, exclude_unset=True)
for field, value in update_data.items():
    setattr(existing_trade, field, value)
```

Metadata survives today only because the aggregator never sets `journal`, so
`exclude_unset=True` filters it out. That is an implicit, untested guarantee. Making
protected trades eligible for this path puts real weight on it.

The update is therefore changed from an exclusion list to an **explicit allow-list** of
broker-derived and aggregate-derived fields, and a regression test asserts that a trade
carrying journal, rating, playbook, note, taxonomy, and annotation retains all of them
across a close-by-import.

### D7 — Manual-close stand-ins suppress sentinel orphan lots

Manual full-close creates a `LogicalExecution` with `origin='manual'` and
`source_id=NULL` (`trade_service.py:951`) and immediately re-aggregates the trade. On a
later import, the broker close for the same contract can become an orphan remainder and
currently creates a sentinel trade (`entry_price = 0.001`). This is a silent corruption
path: the user sees a synthetic trade that affects metrics, while no explicit conflict
is surfaced.

To prevent that failure mode, orphan-lot reconstruction is suppressed when the incoming
orphan close belongs to a contract that has an unresolved manual stand-in candidate:

- at least one non-deleted `origin='manual'` execution with `source_id IS NULL`, and
- at least one non-deleted non-manual execution,
- on the same `(symbol, conid)` and user/account scope.

In that case, the incoming execution remains unlinked and is reported via
`unlinked_executions`/warnings; no sentinel trade is created.

This rule is intentionally conservative: it decides only what is factual (an unlinked
manual stand-in exists on the same contract), and defers identity resolution to the
existing user actions (link the manual leg or delete one leg). It avoids price/time
tolerance heuristics.

### D7 — Suppress the sentinel orphan lot for contracts holding a manual stand-in leg

The suppression at `aggregator.py:683` is keyed on `protected_contracts`, which is
derived from `Trade.is_manually_edited` (`trade_repository.py:1223-1227`). A trade
closed by hand does not reliably carry that flag: `partial_close_trade` sets it on the
partial-close path (`trade_service.py:994`, `:1016`) but not on the full-close path
(`trade_service.py:919-975`). The full-close path only inserts a manual leg and
re-aggregates.

Consequence, traced end to end:

1. Opening leg `E1` (imported), manual closing leg `E2`, later broker closing leg `E3`.
2. `is_manually_edited=false` → the snapshot is empty → no exclusion, no suppression.
3. FIFO consumes all three in `executed_at` order. One closing leg matches, the other
   falls into the orphan branch at `aggregator.py:699` → sentinel trade at
   `entry_price = 0.001`.
4. `_resolve_anchor_trade_ids` maps the matched trade back to the existing row via
   `E1` → UPDATE. The sentinel's anchor resolves to the same trade, which was already
   popped at `import_service.py:609` → falls through to INSERT.
5. `detect_duplicate_pairs` at `:651` cannot fire: the two legs now sit on different
   trades, and the key requires identical direction. `has_unlinked_executions` at `:652`
   cannot fire either — the sentinel *linked* the leftover leg, so nothing is unlinked.

Net effect: a second trade row with a sentinel entry price is persisted and enters every
metric, with `trades_created=1, trades_updated=1, unlinked=0, warnings=[]`.

Suppression is therefore re-keyed: a contract is suppressed when it is held by a closed
protected trade **or** by a trade carrying a `origin='manual', source_id IS NULL` leg.
The second condition is a fact about stored rows, not an inference.

*Why nothing else is needed.* Once the sentinel is gone the leftover execution stays
unlinked, `has_unlinked_for_trade_contracts` (`execution.py:216`) is contract-scoped and
already runs for every rebuilt trade, so `has_unlinked_executions` becomes true on its
own. Both resolution actions exist: delete the manual leg, or link it via
`POST /api/v1/executions/{id}/link` — a mechanism the codebase already documents as the
stand-in contract (`conflict_detection.py:64-68`).

*Alternative considered — auto-pair the manual leg with the incoming broker leg* (match
on contract, direction and quantity within a time tolerance, then soft-delete the manual
leg). Rejected. A hand-typed price and timestamp never match a broker fill exactly, so
the rule needs tolerances, and tolerances are guesses. This is the same class of
implicit, unobservable resolution that produced the defect this change exists to fix.
The system decides what is provable — contract identity, `closed_at`, FIFO quantities —
and hands what is not provable to the user with a flag and an action.

*Alternative considered — set `is_manually_edited=true` on the full-close path* so the
existing suppression applies. Insufficient on its own: it makes suppression depend on a
flag whose meaning is "the user documented this trade", and it would silently widen
isolation for those trades. The flag inconsistency is still worth fixing, but separately
(see Open Question 6).

### D8 — TradeChart semantics follow explicit markers and options context

`TradeChart` currently infers entry/exit legs from trade direction as the primary rule.
That can misclassify legs when `open_close` markers are present and authoritative. The
chart therefore prioritizes `open_close='O'|'C'` and uses direction only as fallback.

Additionally, options trades (trade-level option, or any option leg) suppress generic
horizontal entry/exit price lines. Those lines represent single underlying price anchors
and are misleading for multi-leg option structures.

This is a UI-only interpretation change; no persistence, import, or aggregation behavior
changes.

## Risks / Trade-offs

- **A seed lot leaks into `_finalize_open_lots` and creates a second open trade row.**
  → Highest-severity failure mode of this change: it would turn a stuck-open position
  into a duplicated one. Direct unit test on the aggregator output plus an integration
  assertion that the account's trade count is unchanged after a close-by-import.

- **The allow-list in D6 omits a broker-derived field**, so that field silently stops
  updating. → Derive the list from the model and assert in a test that every
  `Trade` column is classified as either metadata or broker-derived, failing when a new
  column is added without classification.

- **Over-close of a corrected leg produces a confusing remainder.** If the user reduced
  an opening leg from 10 to 3 and the broker closes 5, FIFO matches 3 and 2 become an
  orphan remainder. → Specified behaviour with a warning; strictly better than today
  where nothing happens at all. Surfaced in the import result.

- **Behaviour change is silent for existing users.** Positions that were stuck open
  will start closing on the next import that includes their closing execution, shifting
  historical metrics and the equity curve. → Call it out in the changelog; the shift is
  a correction, not a regression.

- **Over-broad stand-in suppression could hide legitimate transfer-in orphan closes.**
  If the stand-in predicate is too weak, valid sentinel reconstruction could be skipped.
  → Predicate requires both unlinked manual and non-manual legs on the same contract,
  and warning text must indicate "manual stand-in unresolved" so the case is visible.

- **`has_unlinked_executions` semantics narrow.** Trades flagged today because of an
  open-position close will clear their flag. → Intended; the flag is recomputed
  authoritatively on every rebuild (`import_service.py:652`).

## Migration Plan

1. No schema migration. One data-only Alembic migration clears the falsely-set
   `user_modified` markers (D5). It is idempotent and skips any row that does not
   provably match its broker source.
2. Deploy. Existing protected open positions remain as they are.
3. Re-import a broker file whose window covers the orphaned closing executions. The seed
   lot is then present and the position closes. On production this affects two
   executions (`XYZ`-class equities, dated within the last export window), so the
   already-available file suffices.
4. If a required source file is unavailable, the user can link the orphaned execution
   manually via the existing execution-linking UI; a re-aggregation then closes the
   trade. No bespoke repair script is planned.
5. Rollback: revert the deployment. The data model is unchanged, so no state needs
   undoing. Trades closed in the meantime stay closed and correct.

## Open Questions

1. **Open protected trades with a leg carrying `user_modified=true` — seed, or keep
   isolated?** This design seeds them (D2), on the grounds that a corrected entry price
   is an input to the match, not a reason to block it. Currently hypothetical: no such
   trade exists in either dataset (see *Empirical baseline*), so this does not block
   implementation — but it fixes the behaviour for the first one that appears.
2. **Should `merge_trades` really stop marking legs (D4)?** It is the one trade-level
   action that genuinely restructures something. The argument for including it is that
   it restructures *trade grouping*, not execution *values* — the legs remain exactly
   what the broker sent. If merged trades must additionally be frozen against
   re-aggregation, that is a separate requirement and should not be expressed through
   the execution marker.
3. **Do the 9 falsely-marked split children on ATOS and META indicate a second, latent
   defect?** Their split structure has been frozen against every import since the
   markers were set (`delete_split_children_for_account` skips them). Both trades are
   closed, so nothing is visibly wrong today. Worth verifying after the migration that
   both still aggregate correctly.
4. **Should closing a protected position clear `Trade.is_manually_edited`?** No — the
   user's documentation still exists and must keep protecting the trade. Recorded here
   because the opposite is a tempting simplification.
5. **Should `partial_close_trade`'s full-close path set `is_manually_edited`?** The
   partial-close path sets it on both the reduced original (`trade_service.py:994`) and
   the new closed slice (`:1016`), with the comment "prevent broker re-import
   overrides". The full-close path (`:919-975`) does not. D7 removes the phantom-trade
   consequence of that gap, but the asymmetry remains and looks unintentional. Not
   fixed here because changing it widens rebuild isolation for every hand-closed trade,
   which needs its own analysis.

   Related and unverified: the partial-close path creates no `LogicalExecution` and does
   not re-aggregate. It decrements `trade.quantity` directly while the opening leg keeps
   the full quantity, so trade row and legs diverge; `is_manually_edited=true` is what
   stops the next rebuild from recomputing the original quantity. If that reading is
   correct the flag is masking an inconsistency rather than protecting user data. Worth
   tracing before touching either path.

6. **Does the import dialog surface `warnings` and `unlinked_executions` prominently
   enough?** The current failure was invisible to the user because the dialog reports a
   raw-transaction count that reads like success. Fixing the counter is in scope
   (`ImportResult`); the dialog's presentation may need a separate frontend change.
