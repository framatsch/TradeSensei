## Context

The journal is built from three layers:

```
BrokerRawTransaction  →  LogicalExecution  →  Trade (FIFO projection)
   (immutable, dedup)      (mutable app view)     (open lot or round-trip)
```

The domain already models open lots: `LogicalExecution.pnl` is nullable for opening legs, and the FIFO aggregator (`aggregate_executions_fifo_with_sources`) already (a) produces an open `Trade` with no `exit_price`/`closed_at` when a lot is unclosed, and (b) matches later closing legs against existing open lots (`seed_open_lots`, `list_open_lots_by_user`). So "show an open position in the journal" needs **no new trade concept** — it needs an *opening `LogicalExecution` that the aggregator can later close*.

Two brokers want to feed this, with different source data:

| | IBKR `<OpenPosition>` | Schwab `positions[]` |
|---|---|---|
| Opening timestamp | ✅ `openDate` | ❌ snapshot only |
| Stable per-lot id | ✅ `transactionID` (== the `<Trade>`) | ❌ none |
| Cost basis | ✅ `costBasis` | ✅ `averagePrice` / `averageLongPrice` |
| Later close arrives as | a `<Trade>` in a subsequent report | a `TRADE` transaction in a subsequent file |

The question this design settles: **must an open position become a synthetic raw transaction, or can it be a direct open `LogicalExecution` / open `Trade`?** And regardless of that: **how does a snapshot lot reconcile with the broker's own later closing execution without double-counting?**

## Goals / Non-Goals

**Goals:**
- One broker-neutral domain contract: a broker position snapshot → an opening `LogicalExecution` with `origin = "open_position"`, `pnl = None`, that the existing FIFO aggregator treats as an open lot.
- A clean adapter boundary: parsers decide *how* a snapshot becomes a raw record (timestamp, dedup key); the shared layer decides the *domain semantics* (origin, open-lot behaviour, reconciliation).
- Idempotent re-import for both brokers, including brokers with no natural per-lot id.
- Reconciliation: the snapshot lot and the broker's own later close converge on one round-trip `Trade`; if the broker later reports the *opening* execution too, the snapshot lot does not add a second opening leg.

**Non-Goals:**
- Changing FIFO aggregator logic.
- Importing broker `positions[]` for market value / unrealised P&L display (this seeds *trades*, not a live positions view).
- New HTTP endpoints or API schema changes.
- Deciding IBKR- or Schwab-specific parse details here — those live in the respective adapter changes.

## Decisions

### D1: Represent open positions as opening `LogicalExecution(origin="open_position")` — reached via the raw layer

**Options:**
- **A) Synthetic `BrokerRawTransaction` → `LogicalExecution`** (the raw layer does the work).
- **B) Direct `LogicalExecution(origin="open_position")`**, bypassing the raw layer.
- **C) Direct open `Trade`**, bypassing both raw and logical layers.

**Choice: A** (synthetic raw record flagged as open position, then mapped to `origin="open_position"`).

Rationale — this directly answers *"muss es eine synthetische Transaktion sein?"*: **conceptually no, but architecturally yes, and here's why.** The end state we want is identical in all three options — an opening execution that becomes an open lot. The differentiator is not "synthetic vs. real" but **"does the open lot reconcile with the broker's own later close for free?"**

- The raw layer (`BrokerRawTransactionRepository.bulk_upsert`) is the system's **idempotency boundary**: re-importing the same id is a silent no-op. Routing open positions through it means re-imports don't duplicate — reusing infrastructure that already exists.
- The FIFO aggregator matches closes to opens on the instrument key `(symbol, conid, asset_class)` (`aggregator.py:267`), pairing opposite directions in `executed_at` order within that queue. An opening `LogicalExecution` with those fields set correctly is matched by a later close **whether or not** it came from a real execution. So the "synthetic" leg gets automatic reconciliation with zero aggregator changes.
- Option C (direct `Trade`) is rejected: it sidesteps the logical layer, so merges/splits/soft-delete and re-aggregation (which rebuild trades *from* logical executions) would silently drop or duplicate it.
- Option B (direct logical, skip raw) is rejected as the default because it loses the raw-layer idempotency key, forcing bespoke dedup logic in the service for every broker. It remains a *fallback* only if a broker snapshot genuinely cannot be given a stable id (none identified today).

So "synthetic transaction" is a means, not the point. The point is: **reuse the raw idempotency boundary and the FIFO open-lot matching so a snapshot lot behaves exactly like a normal opening leg and closes normally later.**

### D2: Adapter boundary — parsers flag, the shared layer maps

The parser is broker-specific; the origin decision is broker-neutral. To keep brokers from leaking into the service:

- `BrokerRawTransactionCreate` gains a neutral boolean `is_open_position` (default `False`). Parsers set it `True` for snapshot-derived records. No broker enum, no format sniffing in the service.
- `LogicalExecutionService.create_from_raw()` currently hardcodes `origin = EXECUTION_ORIGIN_IMPORTED`. It branches to `EXECUTION_ORIGIN_OPEN_POSITION` when the source raw record has `is_open_position = True`, and forces `pnl = None` for such legs (a snapshot has no realised P&L).

This is the single shared seam. IBKR and Schwab adapters differ only in *how they build the flagged `BrokerRawTransactionCreate`* (D3).

### D3: Per-broker id + timestamp strategy (adapter concern, constrained by this contract)

The contract requires each snapshot record to have a **deterministic, stable raw id** (for idempotency) and a **tz-aware UTC `executed_at`** (for FIFO ordering/matching). How each adapter satisfies it:

- **IBKR** (in `ibkr-open-position-adapter`): id `ibkr:{transactionID}` (matches the eventual `<Trade>`), `executed_at` from `openDate`. This is why IBKR reconciliation is exact — the snapshot and the real opening `<Trade>` share the same id, so `bulk_upsert` collapses them.
- **Schwab** (adapter `schwab-open-position-adapter`, consuming `positions[]`): no per-lot id and no open date. Use a deterministic composite id `schwab:openpos:{accountNumber}:{symbol}:{longQuantity}` and set `executed_at` to `dateRange.start` (ordering-safe: guaranteed to precede any close in the same window — see that adapter's D2). This keeps re-imports idempotent (same file → same id → no-op) but means Schwab reconciliation is **approximate** (D4).

The contract does **not** mandate a specific id format — only that it be deterministic and collision-free per user. Adapters document their scheme.

### D4: Reconciliation — one snapshot-replace rule, plus exact-id fast path

The FIFO aggregator identifies an instrument by the key `(symbol, conid, asset_class)` (`aggregator.py:267`); `direction`/`quantity` only drive open/close pairing *within* that instrument's queue. So a snapshot opening leg and a later closing leg match iff they share `(symbol, conid, asset_class)` and are opposite directions. For Schwab, `conid = None` on both legs — consistent, so matching still works.

Two things must hold: (a) a snapshot lot closes correctly when the real close arrives; (b) the system never ends with a stale or duplicate snapshot lot. Both are covered by **one rule** plus a fast path:

- **Snapshot-replace rule (primary):** position snapshots are the *source of truth* for an account's currently-open lots. On each import carrying snapshots, before seeding, remove existing `open_position`-origin legs for the same `(account_id, symbol, conid, asset_class)` that are not in the new snapshot set. This single rule handles:
  - **Quantity change / omission (B6):** last snapshot said 10 shares, new says 4 (or nothing) → the stale 10-share `open_position` leg is removed, replaced by the current snapshot. No zombie lots.
  - **Supersession by a real execution (B8):** if a real `imported` opening execution now exists for the instrument, the `open_position` leg is dropped in its favour (the real fill time/price is authoritative).
  The rule touches **only** `open_position`-origin legs — `imported`/`manual`/`merged`/`split` are never removed.

- **Exact-id fast path (IBKR):** when a broker provides a shared raw id (IBKR `ibkr:{transactionID}`), the real opening `<Trade>` collapses with the snapshot via `bulk_upsert` (same id → no second leg) before the replace rule even runs. This makes IBKR reconciliation *exact* (true fill time preserved). The replace rule is then a no-op safety net for IBKR.

Closing then happens normally: the surviving opening leg (snapshot or real) is matched by the later closing execution on the shared instrument key; `executed_at` ordering (snapshot `opened_at` from the adapter, see D3) places the open before the close. For id-less brokers the snapshot `opened_at` is approximate until a real opening execution supersedes it — acceptable: an open lot with an approximate open date beats an invisible position.

This guard lives in the import service's re-aggregation prep, not the aggregator.

### D5: `origin = "open_position"` is shared, added once

The origin value and the `raw-transaction-layer` CHECK-constraint widening are defined **here**, not in any adapter change, so there is exactly one delta touching `VALID_ORIGINS` / the DB constraint. The `ibkr-open-position-adapter` and `schwab-open-position-adapter` changes depend on this capability rather than re-declaring the origin. The earlier `ibkr-open-positions-import` change is superseded by `ibkr-open-position-adapter` and should be removed to avoid a duplicate `open_position` origin / `raw-transaction-layer` delta.

## Risks / Trade-offs

- **[Risk] Approximate `opened_at` for id-less brokers (Schwab)** → round-trip P&L is correct (price-based) but holding-period stats are skewed. Mitigation: `open_position` origin marks these; a future "correct open date from confirmed fill" step is possible. Documented, not solved here.
- **[Risk] Double-open or stale lot if the snapshot-replace rule (D4) is wrong** → phantom extra open lot. Mitigation: exact-id path (IBKR) avoids double-open entirely; the replace rule is covered by integration tests for quantity change, omission, supersession-by-real-execution, and guard isolation (never touches non-`open_position` legs).
- **[Risk] Schwab `conid = None` collides across instruments** → the aggregator key `(symbol, None, asset_class)` still separates by symbol + asset_class, so distinct symbols never collide; only two lots of the *same* symbol/asset_class net together, which is the intended snapshot semantics. Acceptable.
- **[Risk] Snapshot quantity ≠ sum of underlying lots** (broker nets multiple fills into one position) → one synthetic opening leg of the netted quantity. Acceptable: FIFO matches partial closes against it; the lot is a single averaged open, which is what a snapshot represents.
- **[Risk] Scope creep vs. surgical-changes rule** → this change is *contract + one shared seam + one origin*, no aggregator changes, no endpoints. The broker parse work stays in the adapter changes.

## Migration Plan

1. Land the origin constant + CHECK-constraint migration + the `is_open_position` flag + the `create_from_raw` branch (this capability). Zero data migration; additive constraint widening.
2. Remove the superseded `ibkr-open-positions-import` change; its parser + keys live in `ibkr-open-position-adapter`, which depends on this contract.
3. Add the Schwab adapter as a follow-up change consuming `positions[]` with D3/D4 semantics.

Rollback: revert the Alembic constraint widening (narrows `origin` back); drain any `open_position` rows first if present. Code-only otherwise.

## Open Questions

- **Should the Schwab adapter be folded into this change or stay a separate follow-up?** Leaning separate (keeps this change a pure contract; Schwab parse detail is substantial). Confirm before writing Schwab tasks.
- **`opened_at` source for id-less snapshots** — resolved for Schwab: `dateRange.start` (ordering-safe; see `schwab-open-position-adapter` D2). A future broker with a per-lot open date should prefer that date.
