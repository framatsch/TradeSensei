## Why

A user who documents an **open** position (writes a note, adds a tag, sets a rating)
permanently loses the ability to have that position closed by a broker import. The
closing execution is imported, stored, and then discarded by the aggregator. The trade
stays open forever, and because the import pipeline is idempotent, no later re-import
can repair it.

This is not an implementation defect — the code behaves exactly as
`openspec/specs/execution-overwrite-protection/spec.md` mandates. The defect is in the
specification: the requirement "metadata-protected trades are isolated from the
projection rebuild" over-generalised the original goal ("do not delete trades the user
has documented") into full immutability, including immunity from receiving new
execution legs.

Observed in production: 21 of 452 trades are metadata-protected; 2 closing executions
are permanently unlinked; 2 positions are stuck open.

---

## The problem, worked through on an anonymised example

### Cast

| Entity | Value |
|---|---|
| Instrument | `XYZ` (equity, no contract id — the broker does not supply one) |
| Account | `A1`, broker type `<broker>`, raw-pipeline capable (implements `parse_raw`) |
| User | `U` |

### Timeline

**Day 1 — the position is opened**

The broker file contains one execution:

```
activity 1001   XYZ   BUY   10 @ 100.00   positionEffect=OPENING
```

The import produces:

```
broker_raw_transactions   R1 = "<user>:<broker>:1001"      open_close='O'
logical_executions        E1  LONG 10 @ 100.00  open_close='O'  user_modified=false  trade_id=T1
trades                    T1  XYZ LONG 10  entry=100.00  closed_at=NULL
                              is_manually_edited=false
```

Everything is correct.

**Day 2 — the user documents the still-open position**

The user opens `T1` and writes a note: *"entered on pullback, watching the 95 level"*.
(The same happens for a tag, a rating, a playbook assignment, a trade edit, or a trade
merge — all five paths behave identically.)

`NoteService.create` (`backend/app/services/note_service.py:85-86`) executes:

```python
await TradeRepository(...).mark_manually_edited(trade_id, user_id)   # T1.is_manually_edited = true
await self._execution_repo.mark_user_modified_for_trade(trade_id)    # E1.user_modified   = true
```

Two protection markers are now set. Note that **nothing about the execution was
edited** — the note is pure metadata. The second call is collateral damage.

State:

```
logical_executions   E1  ... user_modified=TRUE
trades               T1  ... is_manually_edited=TRUE
```

**Day 30 — the position is closed at the broker**

The next broker file contains both executions (brokers export a date window, so the
opening execution appears again):

```
activity 1001   XYZ   BUY    10 @ 100.00   positionEffect=OPENING    <- already imported
activity 2002   XYZ   SELL   10 @ 120.00   positionEffect=CLOSING    <- new
```

The user imports it and expects `T1` to close with a +200.00 profit.

### What actually happens, step by step

**Step 1 — raw layer: correct.**
`R1` already exists and is skipped by `ON CONFLICT DO NOTHING`. `R2` is inserted.
`inserted_raw_ids = {R2}` → `should_rebuild_projection = True`.

**Step 2 — logical layer: correct.**
`E2` is created 1:1 from `R2`:

```
logical_executions   E2  SHORT 10 @ 120.00  open_close='C'  user_modified=false  trade_id=NULL
```

At this point the database contains everything needed to close the trade.

**Step 3 — the protection snapshot captures the open position.**
`ImportService._resolve_protected_execution_snapshot` (`import_service.py:1695`)
collects every trade with `is_manually_edited = true` and all of their active legs:

```
protected_snapshot.trade_ids     = { T1 }
protected_snapshot.execution_ids = { E1 }          <- the OPENING leg
protected_snapshot.contracts     = { ("XYZ", None) }
```

**Step 4 — the opening leg is removed from the aggregation input.**
`_iter_trade_creates_from_logical_batches` (`import_service.py:1777`):

```python
if logical_row.id in excluded_ids:
    continue
```

`E1` is dropped. The FIFO aggregator receives **only** `E2`.
Mandated by `spec.md:525`.

**Step 5 — the closing leg is discarded.**
`aggregate_executions_fifo` (`aggregator.py:659-690`) processes `E2`:

- key `("XYZ", None, "EQUITY")` → queue is empty (because `E1` was removed in step 4)
- `is_closing_leg = exec_trade.pnl is not None` → `True`
- therefore this looks like an orphaned close, and the sentinel-orphan branch is entered
- but `("XYZ", None)` is in `protected_contracts`:

```python
if protected_contracts and (symbol, conid) in protected_contracts:
    logger.warning("suppressed_orphan_lot_for_protected_contract ...")
    continue          # <-- E2 leaves the pipeline here, permanently
```

Mandated by `spec.md:571`. The aggregator returns `[]`.

**Step 6 — the trade is skipped, the execution is flagged.**
`T1` is preserved from deletion twice over (`is_manually_edited` in
`delete_by_user_account`, plus `exclude_trade_ids`), receives no field update
(`import_service.py:584-594`), and the import reports:

```
unlinked_executions = 1
warnings            = ["protected_unlinked_execution: symbol=XYZ executed_at=..."]
T1.has_unlinked_executions = true
```

Mandated by `spec.md:551`. The user-visible import counter shows
`raw_transactions_created = 1`, which reads like "1 imported" and hides the failure.

**Step 7 — the damage is permanent.**
The user re-imports the same file to fix it. Now `R2` already exists, so
`inserted_raw_ids` is empty and `should_rebuild_projection` is `False`. The pipeline
takes the zero-insert early return (`import_service.py:406-422`) and reports
`trades_created = 0`. There is no self-healing path — the only escape today is
`overwrite_manually_edited=true`, which is precisely the operation the user's note was
meant to protect against.

### Final state

```
trades              T1  XYZ LONG 10  closed_at=NULL  is_manually_edited=true
                                     has_unlinked_executions=true
logical_executions  E1  LONG  10 @ 100.00  trade_id=T1
                    E2  SHORT 10 @ 120.00  trade_id=NULL    <- orphaned forever
```

The position is closed at the broker but open in the application, the realised P&L of
+200.00 is missing from every metric, and the equity curve is wrong.

### The reproduction, isolated

Running the aggregator directly reproduces step 5 in two lines:

```
A) both legs present, no protection
   -> XYZ LONG 10  closed_at=2026-09-02 13:30:03        OK

B) opening leg excluded + contract protected  (= the real import path)
   -> []
      suppressed_orphan_lot_for_protected_contract symbol=XYZ conid=None
```

---

## Root cause

One flag, `Trade.is_manually_edited`, currently governs three unrelated concerns:

| | Concern | Correct? |
|---|---|---|
| a | The trade row must not be deleted; journal, notes, tags, rating, playbook survive a rebuild | **Yes** — this was the original goal |
| b | Existing execution legs must not be overwritten, reassigned, or deleted | **Yes** |
| c | The trade takes no part in FIFO at all; its contract is blacklisted; no field updates | **No** — this is what breaks closing |

Concern (c) is unnecessary for (a) and (b), and it is the sole cause of the defect.

A trade is a *projection* derived from its executions — it is not an append-only
entity. Appending a closing leg therefore necessarily requires recomputing
`closed_at`, `exit_price`, `pnl`, `net_pnl`, and `quantity`. Today's spec forbids
exactly that ("SHALL NOT apply any field update to the trade"), so the two requirements
are mutually exclusive by construction.

Separately, five trade-level paths — `NoteService`, `TradeMetadataService`,
`TradeService.update` (`trade_service.py:599`) and `TradeService.merge_trades`
(`trade_service.py:864-865`) — set `LogicalExecution.user_modified = true`. That marker
is specified as meaning "the user edited this execution" (`spec.md:4-5`), which is
untrue in all of these cases. It widens the blast radius from one trade to every
contract that trade holds.

Measured on both the production and the local dataset: of 63 executions carrying the
marker, **zero** differ from the broker data. There are no `merged` executions at all,
and split children are created without the marker. Every marker in existence is
collateral.

### Additional safeguard: manual full-close stand-ins

There is a second failure mode adjacent to the main defect: a user can fully close a
trade manually, then later import the broker close for the same contract. Today this can
materialize as a sentinel orphan trade (`entry_price = 0.001`) instead of a visible
actionable mismatch.

This change makes that mismatch explicit rather than synthetic: when a contract has an
unresolved manual stand-in leg (`origin='manual'`, `source_id IS NULL`) plus non-manual
legs, sentinel orphan reconstruction is suppressed, the broker close remains unlinked,
and the import reports a warning. The user resolves it via existing flows (link the
manual leg or delete one duplicate leg). No automatic pairing heuristics are introduced.

---

## What Changes

- **Open** metadata-protected trades participate in the projection rebuild as **seed
  lots**: their active legs enter the FIFO input carrying `db_trade_id`, so an incoming
  closing execution matches them and the existing trade row is **updated in place**
  instead of being skipped. This reuses the mechanism that already exists for open
  COMBO positions (`_build_seed_combo_execution_trades`, `import_service.py:1795`, and
  the "closes an existing open DB lot (UPDATE)" path at `import_service.py:740`).
- **Closed** metadata-protected trades stay fully isolated, unchanged from today. A new
  closing execution for an already-closed position is a genuinely new trade, not an
  amendment.
- The `protected_contracts` orphan suppression no longer applies to contracts held by
  an **open** protected trade — with the seed lot present the FIFO queue is not empty,
  so no sentinel orphan can arise in the first place.
- Aggregate fields (`closed_at`, `exit_price`, `quantity`, `pnl`, `net_pnl`,
  `commission`) are recomputed for a protected trade when its leg set changes.
  User-supplied metadata columns and related rows are never written by the import.
- `NoteService`, `TradeMetadataService`, `TradeService.update` and
  `TradeService.merge_trades` stop calling `mark_user_modified_for_trade()`. These
  actions continue to set `Trade.is_manually_edited` (deletion protection); they no
  longer claim the user edited an execution.
- A one-off data migration clears the falsely-set markers. Measurement of both datasets
  shows **every** existing `user_modified=true` execution is collateral from a
  trade-level action — none reflects an actual execution edit (see design.md,
  *Empirical baseline*).
- Legs carrying a genuine `user_modified = true` are still never overwritten,
  reassigned, or deleted; their stored (user-corrected) values are what the seed lot is
  built from.
- Frontend trade-chart execution classification prefers explicit `open_close` markers
  (`O`/`C`) over direction fallback, and options trades suppress generic entry/exit
  horizontal price lines to avoid misleading overlays.
- The import result distinguishes "position closed against a protected trade" from
  "execution could not be linked", so the counter no longer reads as success.
- Orphan suppression additionally covers contracts held by a trade carrying a **manual
  stand-in leg** (`origin='manual'`, `source_id IS NULL`). A position closed by hand,
  whose real broker fill arrives in a later import, currently produces a persisted
  sentinel trade at `entry_price = 0.001` with no warning and no flag, because
  `is_manually_edited` is only set on the partial-close path. The leftover execution is
  now left unlinked instead, which makes the existing
  `has_unlinked_executions` flag and the existing resolution actions (delete the manual
  leg, or link it via `POST /api/v1/executions/{id}/link`) apply. No automatic pairing
  of the manual leg with the broker leg is introduced — see design.md D7.
- For manual stand-in unresolved cases, at least one trade on the affected contract is
  flagged with `has_unlinked_executions=true`, and the trading overview can isolate
  these cases through the existing `has_unlinked_executions=true` trade-list filter
  (system filter: "Needs linking").

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `execution-overwrite-protection`: three requirements change.
  - *Metadata-protected trades are isolated from the projection rebuild* — narrowed to
    closed trades; open protected trades take part as immutable seed lots and may
    receive recomputed aggregate fields.
  - *Orphan lot suppression for protected contracts* — no longer applies to contracts
    held by an open protected trade.
  - A new requirement extends orphan suppression to contracts held by a trade with a
    manual stand-in leg, so a hand-closed position never produces a sentinel trade when
    its broker fill is imported later.
  - *Unlinkable executions are reported and flagged* — a closing execution matched
    against an open protected trade is linked, not reported as unlinked.
  - A new requirement fixes the marker semantics: pure metadata mutations SHALL NOT set
    `LogicalExecution.user_modified`.
  - A new requirement guarantees that a protected trade's metadata is never written by
    an import, even on the new update path.

## Impact

**Backend**

- `backend/app/services/import_service.py` — protection snapshot split by open/closed;
  seed-lot construction for open protected trades; update path for protected trades;
  reporting.
- `backend/app/utils/parsers/aggregator.py` — `protected_contracts` scope narrowed for
  open protected trades, widened to cover contracts holding a manual stand-in leg
  (`aggregator.py:683`, `:815`).
- `backend/app/repositories/execution.py` — query resolving contracts that hold an
  unlinked `origin='manual'` leg.
- `backend/app/services/note_service.py`, `backend/app/services/trade_metadata_service.py`,
  `backend/app/services/trade_service.py` (`update`, `merge_trades`) — drop
  `mark_user_modified_for_trade()`.
- `backend/app/schemas/imports.py` — `ImportResult` reporting fields.
- `backend/alembic/versions/` — one data-only migration clearing false markers.

**Risk**

- `TradeCreate` carries a `journal` field (`backend/app/schemas/trade.py:112`). The
  update path at `import_service.py:596-601` relies solely on `exclude_unset=True` to
  avoid clobbering it. Making protected trades eligible for updates puts weight on that
  implicit guarantee; it must be covered by an explicit regression test, otherwise the
  original bug (documented trades losing their documentation) returns in a subtler form.

**Data**

- One idempotent, data-only migration clearing 63 falsely-set `user_modified` markers
  (54 prod / 50 local `imported`, 9 `split`). `Trade.is_manually_edited` is not touched.
- Side effect being repaired: `delete_split_children_for_account` skips
  `user_modified=true` rows, so the 9 marked split children on ATOS and META have been
  frozen against every rebuild since the markers were set.

**Stuck records**

- The 2 currently orphaned closing executions in production resolve on the next import
  of a file containing them, because the seed lot will then be present. If that file is
  no longer available, a one-off repair is needed — to be decided during implementation.
