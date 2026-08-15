## Why

The corporate-action data layer is complete and correct, and some disclosure UI already
exists — but a key part of it **misleads the user**. The table shows the persisted `Trade`
values, whose basis depends on the holding-period rule:

- A trade **closed before** a split keeps its **original, as-traded** values in the table;
  only the chart restates them. Table and chart legitimately differ.
- A trade **held across** a split has its entry **split-normalised** onto the post-action
  share unit — e.g. across a 1:10 forward split, an entry bought at `100 × 10` persists as
  `10 × 100`, while the opening leg's `raw_price`/`raw_quantity` still record the original
  `100 × 10` (this is independent of the leg's `origin` — `origin='split'` is an unrelated
  concept, see design.md). Here the table is **not** the as-traded value.

The gaps:

- The split badge in the table already exists (`TradeRow.tsx:119-138`), but its tooltip
  reads "Values shown are historical. Chart is adjusted." — **false** for a held-across
  trade, where the table shows split-normalised, not original, values.
- The corporate-action event row in the execution list already exists
  (`ExecutionLegsTable.tsx:257`); its presentation-only, value-free nature needs to be
  pinned down by spec + tests so it can never drift into leg totals.
- Execution rows display adjusted price only, discarding the already-available
  `raw_price`/`raw_quantity` pair (`ExecutionRow.tsx:249-250`), so the original as-traded
  value is not shown inline next to the adjusted one.

This is a disclosure-accuracy gap, not a data-correctness gap: the numbers are right, but
the app does not honestly explain why they differ across views.

## What Changes

The unifying principle: **one value basis across the whole numeric journal (table, header,
Execution Summary, execution legs) — the as-traded / persisted basis — and the chart is the
only adjusted surface.** This replaces today's split state where header and summary are
persisted but the legs render adjusted, so legs did not reconcile to the header.

- **Unify the execution legs onto the as-traded basis.** `ExecutionRow` today displays
  adjusted `price`/`quantity` by default (with a `suppressAdjustedValues` fallback only for
  closed-before-split trades) and even computes notional from adjusted values while other
  cells can be raw (`ExecutionRow.tsx:255,424`) — an in-row contradiction. Make `raw_*` the
  uniform primary display and compute notional from the same basis, so legs reconcile to the
  header and the Execution Summary (which are already persisted/raw). The `Execution
  Summary` (`ExecutionSummaryCard.tsx` — COMBO uses `raw_*`, single uses `trade.*`) and the
  `SplitExecutionModal` are already on this basis and need no change. As a side effect, the
  legs' edit inputs (already seeded from `raw_*`) stop mismatching the displayed value.
- **Keep the chart adjusted, and disclose it.** The chart stays on the provider-adjusted
  axis (markers at adjusted price with `<adjusted> (raw: <raw>)`, per the existing
  split-adjusted-execution-markers capability). The detail view discloses near the chart
  that the numeric values are as-traded while the chart is split-adjusted — replacing the
  now-inverted banner ("header values are chart-adjusted…") and fixing its visibility
  condition to key off corporate-action impact instead of `quantity == chart_quantity`.
- **Trade table discrepancy indicator + honest tooltip.** The split badge
  (`TradeRow.tsx:119-138`) stays, but its tooltip ("Values shown are historical. Chart is
  adjusted.") is reframed as a *discrepancy signal* that names the applicable actions and
  points to the trade detail, without asserting the row shows original values (false for a
  held-across-split trade).
- **Corporate action as a timeline event in trade details.** The event row already exists
  (`ExecutionLegsTable.tsx:257`); confirm and formalise (spec + tests) that it stays
  presentation-only — derived from `corporate_action_impact`, **not** a `LogicalExecution`,
  carrying no P&L, quantity, price, or commission, never persisted, excluded from all leg
  totals and COMBO summaries.
- **Per-leg chart-restatement provenance.** Because a split restates only the legs held
  across its effective date, the detail view marks *which* legs the chart restates: a
  restated leg is visibly marked while its primary displayed value stays as-traded; an
  untouched leg is not marked. The exact way the adjusted counterpart is surfaced for a
  restated leg (inline hint vs. mark-only) is an open design question below.

Explicitly **out of scope** (deferred, see design Open Questions):

- **Global historical/chart-adjusted basis toggle** for the whole table. It conflicts
  with "table shows realised, historical-basis truth" and risks presenting
  `adjusted_price × adjusted_quantity` as if it were realised PnL. Deferred pending an
  explicit product decision; not part of this change.
- **Reverse-split fractional remainder / cash-in-lieu presentation.** How a residual
  fractional share (e.g. reverse 1:3 on 100 → 33.33) is displayed in the timeline row
  is an open question below; this change ships the event row without asserting a
  rounding-display rule.
- Any change to adjustment arithmetic, holding-period semantics, persistence, or the
  executions/trade API contract. All required data already exists.

## Capabilities

### New Capabilities

- `corporate-action-ui-disclosure`: Presentation-layer disclosure of corporate-action
  impact — a trade-table split indicator with an explanatory tooltip, a derived
  (non-persisted) corporate-action event row in the trade-detail execution timeline, and
  per-execution raw-vs-adjusted value display — so users can reconcile the historical,
  chart-adjusted, and provider-adjusted values already present in the app.

### Modified Capabilities

<!-- None. The data contracts of corporate-action-lifecycle and
     split-adjusted-execution-markers are unchanged; this change consumes them. -->

## Impact

- **Frontend only.**
  - `frontend/components/trades/TradeRow.tsx` — split badge + tooltip (consumes
    existing `Trade.corporate_action_impact`).
  - `frontend/components/trades/ExecutionLegsTable.tsx` — interleave the derived
    corporate-action event row between legs by effective date.
  - `frontend/components/trades/ExecutionRow.tsx` — raw-vs-adjusted inline display
    (consumes existing `raw_price`/`raw_quantity`).
  - Possible small shared formatter reuse from
    `frontend/lib/executionPriceLabel.ts` for the dual-value string.
- **Backend / APIs / migrations**: none. No new fields, no schema change, no OpenAPI
  regeneration required (all consumed fields already exist in the generated client).
- **Dependencies / external services**: none.
