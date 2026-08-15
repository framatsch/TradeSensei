# Design — corporate-action-ui-disclosure

## Context

The original proposal (a Frontend-team suggestion) recommended: a split badge + tooltip
in the trade table, a corporate action as an "event row" in the execution timeline, and
an optional global historical/adjusted basis toggle. This design records which of those
are safe to ship, which raise questions, and why — grounded in what the codebase already
provides.

The data layer is already done. Two archived changes cover it:

- `corporate-action-lifecycle` — persists historical-basis `Trade` values, derives
  chart-adjusted counterparts on read (`chart_quantity`, `chart_entry_price`,
  `chart_exit_price`), and exposes `corporate_action_impact` on the trade read model.
- `split-adjusted-execution-markers` — computes adjusted execution values on-the-fly and
  exposes `raw_price`/`raw_quantity` per leg; chart markers already render
  `<adjusted> (raw: <raw>)` via `frontend/lib/executionPriceLabel.ts`.

So this change is **pure presentation**. No arithmetic, no persistence, no API change.

## Already-resolved questions (do not re-litigate)

These were raised as concerns against the original suggestion but are already settled by
existing specs; the design notes them so reviewers don't reopen them:

1. **Forward vs. reverse split, and multiple compounding splits.** Handled — adjustment
   is `quantity × ∏ratio`, `price ÷ ∏ratio` over all applicable actions
   (`split-adjusted-execution-markers`). The UI consumes results; it does not compute.
2. **Adjustment window / double-adjustment.** Handled by the holding-period rule and the
   effective-date boundary in `corporate-action-lifecycle` (execution *on* the effective
   date is post-split; comparison uses exchange-local date). The UI does not decide
   which legs are adjusted.
3. **Source of adjusted values.** Handled — executions carry both bases; the trade header
   carries `chart_*`. The UI never divides by a ratio itself; it reuses server-provided
   pairs.
4. **Commission is never scaled.** Handled in the data layer; the event row shows no
   commission at all, so there is no risk of implying a scaled commission.

## Decisions

### Decision 1 — The corporate-action timeline row is presentation-only, never a leg

The event row is derived from `Trade.corporate_action_impact[]` and injected into the
rendered execution list by effective date. It MUST NOT be a `LogicalExecution`, MUST NOT
be persisted, and MUST NOT carry price, quantity, P&L, or commission. Rendering it as a
pseudo-execution with numbers would recreate exactly the basis-confusion this change
exists to remove, and would risk a future reader summing it into totals.

- *Alternative rejected:* materialise a synthetic execution so the list is "uniform".
  Rejected — it pollutes the immutable logical layer's mental model and invites
  accidental inclusion in aggregates.

### Decision 2 — Keep the persisted basis in the table; badge is a discrepancy signal

The table keeps rendering the persisted `Trade` values unchanged. Those values are not one
uniform basis across all trades — they follow the holding-period rule:

- **Closed before the split:** persisted = original as-traded (raw). Only the chart
  restates them. Table and chart differ, and that is correct.
- **Held across the split:** persisted entry is split-normalised onto the post-action share
  unit (so entry unit = exit unit and realised PnL is right). Here the table equals the
  chart-adjusted header and differs from the original as-traded values, which remain
  visible as the trade's execution legs on the detail page.

Because the basis is not uniform, the badge tooltip MUST NOT assert a single basis label
("values are historical"). It is a **discrepancy signal**: it flags that a corporate action
applies and that numbers may differ across table / chart / original trade, and it routes the
user to the detail page for the reconciled per-leg values. We do not show two numbers per
cell in the table (too noisy for a list view); dual values belong in the detail view and on
the chart, where there is room and context.

*Illustration (synthetic):* a trade held across a 1:10 forward split (ratio `10`) whose
entry was bought at `price 100 × quantity 10` persists `entry_price = 10` and
`quantity = 100` (the split-normalised entry), while the opening leg's `raw_price`/
`raw_quantity` still carry the original `100 × 10`, independent of that leg's `origin`
(see the "origin='split' is unrelated" note below — do not assume the opening leg's
`origin` is `'split'`). The old "values are historical" tooltip claimed the table shows
the original trade — here it shows `10`, not `100` — which is why it is being corrected.

**Correction — `origin='split'` is unrelated to corporate actions.** An earlier draft of
this document assumed the leg preserving a held-across trade's original values was
identifiable by `origin='split'`. That is false. Verified in the backend
(`aggregator.py:_apply_split_event`): corporate-action adjustment mutates in-memory FIFO
lot quantities/prices during aggregation and never creates a `LogicalExecution` row.
`origin='split'` is created exclusively by two unrelated mechanisms: the manual
"Split Execution" dialog (`api/v1/executions.py`, `SplitExecutionRequest`) and the import
backfill's proportional-allocation step (`import_service.py`). A leg's `raw_price`/
`raw_quantity` — not its `origin` — is what carries the original as-traded values,
regardless of whether that leg happens to also be a split child. The two concepts are
independent and can co-occur or not; neither implies the other.

### Decision 3 — One basis across the numeric journal; only the chart is adjusted

The root inconsistency the user identified is that different surfaces use different bases
with no governing rule: the table/header/summary show persisted values while the execution
legs show adjusted values, and `ExecutionRow` even mixes bases within a single row (notional
from adjusted while price/qty could be raw). The blast-radius analysis showed the fix is
small and one-directional:

- **Execution Summary** (`ExecutionSummaryCard.tsx`) is already as-traded — COMBO uses
  `raw_*`, single-instrument uses `trade.*`. No change.
- **SplitExecutionModal** is already `raw_*`. No change.
- **Chart** (`TradeChart.tsx`) is already adjusted and must stay so (adjusted OHLCV axis).
  No change.
- **Only `ExecutionRow`** displays adjusted by default. Switch it to as-traded (`raw_*`) as
  the uniform primary, and compute notional from that same basis, removing the in-row
  contradiction and the closed-before-split-only `suppressAdjustedValues` special case.

The spec's "split-adjusted-execution-markers" requirements do not conflict: every "SHALL …
adjusted" there is scoped to backend computation, the API shape, or the **chart markers** —
never to the executions table display. So making the table as-traded is spec-compatible.

Consequence for dual values: in the numeric journal we no longer show `<adjusted> (raw: …)`
as a per-cell default. The as-traded value is primary; the adjusted counterpart is a
*provenance* detail for restated legs (see OQ5), not a co-equal number. The
`<adjusted> (raw: <raw>)` format remains where it belongs — on the chart markers.

## Open Questions (must be resolved before or during implementation)

### OQ1 — RESOLVED — Which basis does the trade table show?

The table binds the persisted `Trade` fields `entry_price`/`exit_price`/`quantity`/`pnl`
(`TradeRow.tsx:150,156,159,161`), never the `chart_*` fields. Those persisted values are
raw for closed-before-split trades and split-normalised for held-across-split trades (see
Decision 2). The tooltip is therefore reframed as a discrepancy signal and no longer claims
the row is "historical/original". Resolved; the spec's "Trade Table Value Basis Is
Documented, Not Changed" requirement records the rule.

### OQ2 — Global basis toggle: ship, defer, or drop?

The original suggestion proposed a table-wide "show historical / show chart-adjusted"
toggle. Risk: an adjusted view of the table can imply `adjusted_price ×
adjusted_quantity` is realised PnL, which it is not. **Recommendation: defer** — ship the
disclosure (badge/tooltip/event row) first, measure whether users still ask for a toggle,
and only then design it with an explicit "this is a chart-alignment view, not a PnL view"
guard. Needs a product decision, not an engineering one.

### OQ3 — Fractional remainder / cash-in-lieu display in the event row

A reverse split can leave a fractional share the broker liquidates for cash-in-lieu. The
data layer handles the arithmetic, but **how the event row communicates a residual
fraction** (show it, footnote it, ignore it) is undecided. This change ships the event
row without asserting a rounding-display rule; the rule is a follow-up once we confirm how
often cash-in-lieu appears in real imported data.

### OQ4 — Symbol remap (old_conid → new_conid) presentation

`corporate_action_impact` carries `old_conid`/`new_conid`. When a corporate action also
remaps the symbol/instrument, the timeline event and the badge tooltip may need to show
"TICKER_A → TICKER_B". **Undecided** whether this change surfaces the remap or leaves it
for a later iteration. Recommend: show it in the tooltip if the values differ, but treat
copy as provisional.

### OQ5 — RESOLVED (revised) — How is a restated leg's adjusted counterpart surfaced?

With the legs now as-traded (Decision 3), a leg the chart restates still benefits from
showing *what* the chart uses, so the user can connect a leg to its marker. Directional
decision (user): keep an optional adjusted hint on restated legs rather than dropping the
adjusted value from the detail entirely — i.e. as-traded is primary, adjusted is secondary
provenance.

**First implementation (superseded):** an inline `(adjusted: …)` text suffix next to the
as-traded primary value. This worked but left the leg's chart-adjustment cue as *text*,
duplicating a *separate* `Split`-icon badge that was placed in the status column for the
same fact (see the icon-unification pass) — one leg ended up with two independent visual
cues for one piece of information: a text suffix in the value cell, and an icon in the
status column. This is exactly the redundancy the user's original complaint (about a
"better symbol") was trying to avoid, and it resurfaced once the icon was introduced without
removing the older text suffix.

**Final resolution:** the status-column badge is removed entirely. The `Split` icon moves
*into* the value cells, replacing the word "adjusted" inside the parentheses:
`<DualValueWithIcon>` renders `<as-traded>` when equal, or `<as-traded> (<Split
icon><adjusted>)` when they differ — one cue, in one place, per value. The icon's wrapping
element carries a `title` with the concrete adjusted figure, so the information is not lost,
only moved from a redundant second location into the same parenthetical that already existed
for this purpose. Applied to both the price and the quantity cells, in both the active and
deleted-row branches.

## Risks / Trade-offs

- **Tooltip accuracy depends on OQ1.** If a table cell's basis is misidentified, the
  disclosure becomes misinformation — worse than no disclosure. Verification is a
  prerequisite, not a nicety.
- **Event-row placement depends on correct chronological ordering** relative to legs
  whose displayed timestamps may be in different bases; the row must be ordered by the
  action's effective date against the legs' actual execution dates, not by any adjusted
  display value.
- **Switching legs to as-traded changes existing tests.** `ExecutionRow.test.tsx` expects
  adjusted-as-primary (`"$150.00 (raw: $50.00)"`); it must be updated to the as-traded
  primary. Chart/`formatPriceLabel` tests stay valid (chart unchanged).
- **Perceived "chart doesn't match my numbers".** Mitigated by the near-chart disclosure and
  the per-leg provenance mark; the chart divergence becomes an explained property.

## Migration / Rollout

None. Frontend-only, additive, no data or API change. Can ship behind the existing
`corporate_action_impact` presence check with no feature flag required.
