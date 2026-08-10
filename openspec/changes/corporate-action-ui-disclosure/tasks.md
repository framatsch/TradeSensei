# Tasks — corporate-action-ui-disclosure

> Context: an earlier pass shipped the split badge (`TradeRow.tsx:119-138`), the
> corporate-action event row (`ExecutionLegsTable.tsx:257`), and a detail banner. This
> change **corrects and unifies** the value basis: one as-traded basis across the whole
> numeric journal, with the chart as the only adjusted surface, plus honest disclosure via
> one consistent icon.

## 0. Resolved decisions

- [x] 0.1 (OQ1) Table binds persisted `entry_price`/`exit_price`/`quantity`/`pnl`
  (`TradeRow.tsx:150,156,159,161`), never `chart_*`. Raw for closed-before-split, split-
  normalised for held-across-split. Tooltip must NOT claim "historical/original".
- [x] 0.2 (OQ4) Symbol remap (`old_conid != new_conid`) surfaced in the tooltip as
  "(Symbol changed)".
- [x] 0.3 (OQ2) Global basis toggle: deferred, out of scope.
- [x] 0.4 (OQ3) Event row ships without a fractional-remainder / cash-in-lieu display rule.
- [x] 0.5 (OQ5) Resolved twice: first as an inline `(adjusted: …)` text suffix, then
  corrected (see task 7) to an inline `Split` icon in parentheses instead of the word
  "adjusted" — one shared icon, not a second text-based cue.
- [x] 0.6 **Correction:** `origin='split'` is unrelated to corporate actions. Verified in
  `aggregator.py:_apply_split_event` — corporate-action adjustment mutates in-memory FIFO
  lots and never creates a `LogicalExecution` row. `origin='split'` is created only by the
  manual "Split Execution" dialog and the import backfill's proportional-allocation step
  (`api/v1/executions.py`, `import_service.py`). A leg's `raw_price`/`raw_quantity` — not
  its `origin` — carries the as-traded values. `design.md`/`proposal.md`/`spec.md` are
  corrected to not imply otherwise.

## 1. Unify execution legs onto the as-traded basis (core change)

- [x] 1.1 In `ExecutionRow.tsx`, `raw_price`/`raw_quantity` are the primary displayed price
  and quantity for every leg (active + deleted branches); the adjusted-by-default display
  and the closed-before-split-only `suppressAdjustedValues` special case are gone.
- [x] 1.2 Fixed the in-row basis mix: notional (`ExecutionRow.tsx`) computed from
  `raw_quantity × raw_price × multiplier`, matching the displayed price/quantity.
- [x] 1.3 Removed the `suppressAdjustedValues` prop from `ExecutionRow` and its pass-through
  in `ExecutionLegsTable.tsx`; `isClosedBeforeSplit` is retained only for the event-row
  placement gate, which is unrelated to leg display basis.
- [x] 1.4 Confirmed `ExecutionSummaryCard.tsx` (COMBO=`raw_*`, single=`trade.*`) and
  `SplitExecutionModal.tsx` (already `raw_*`) needed no change; legs now reconcile to them.

## 2. Keep the chart adjusted + disclose it near the chart

- [x] 2.1 Chart stays on the adjusted axis with `<adjusted> (raw: <raw>)` markers
  (`TradeChart.tsx`, `executionPriceLabel.ts`) — no change.
- [x] 2.2 Replaced the inverted detail banner with an as-traded-vs-chart disclosure and
  fixed its visibility to key off `corporate_action_impact`, not `quantity == chart_quantity`
  (`page.tsx:388-392`).

## 3. Unify the corporate-action icon (single visual cue everywhere)

- [x] 3.1 Adopted the split-arrow (`Split` from lucide) as the one corporate-action icon,
  visually distinct from the execution-splitting `origin='split'` vocabulary (see 0.6).
- [x] 3.2 Trade-table indicator: `Scissors` → `Split` (`TradeRow.tsx:140`), and removed the
  wrong visibility gate (`quantity === chart_quantity`) so it shows whenever
  `corporate_action_impact` is non-empty.
- [x] 3.3 Event row: `Scissors` → `Split` (`ExecutionLegsTable.tsx:260`).
- [x] 3.4 Detail chart-basis disclosure: prefixed with the `Split` icon (`page.tsx:388-392`).
- [x] 3.5 Chart-level marker: `buildCorporateActionMarkers` (`TradeChart.tsx`) renders one
  amber circle marker per corporate action at its effective date (clamped to the visible
  candle range), labelled "Split <ratio> on <date>" — same wording as the event row, same
  amber tone as the disclosure banner (`--warning`). lightweight-charts markers are
  canvas-drawn (`shape: circle/square/arrowUp/arrowDown`, no embeddable SVG icon), so this
  is the closest chart-native equivalent of the `Split` icon used elsewhere.

## 4. Per-leg chart-restatement provenance — inline icon, not a separate badge

*Superseded twice: v1 was a text "Adjusted" status-column badge; v2 replaced the text with
a `Split` icon but kept it in the status column while ALSO leaving `(adjusted: …)` text in
the value cells — redundant. Final: the icon lives INSIDE the value cells, replacing the
text, and the separate status-column mark is removed entirely.*

- [x] 4.1 Removed the status-column "Adjusted"/`Split`-icon badge from `ExecutionRow.tsx`
  (was next to `ExecutionStatusBadge`) — now redundant with 4.2.
- [x] 4.2 Added `DualValueWithIcon` (`ExecutionRow.tsx`): renders the as-traded value as
  plain text, and — only when the chart-adjusted value differs — appends
  `(<Split icon/><adjusted value>)` in place of the as-traded value's old
  `(adjusted: …)` text suffix. Applied to both the price and quantity cells, in both the
  active and deleted-row branches.
- [x] 4.3 The icon's wrapping element carries a `title` with the concrete adjusted value
  (e.g. "The price chart shows this value as $150.00 (split-adjusted)..."), satisfying the
  "icon has an accessible label" requirement without a redundant status-column mark.
- [x] 4.4 Removed the now-unused `formatDualValueLabel` import from `ExecutionRow.tsx`
  (its generalised `secondaryLabel` param remains used by the chart's `formatPriceLabel`).

## 5. Trade table indicator + event row (already shipped; formalise + guard)

- [x] 5.1 Badge shown only when `corporate_action_impact?.length` (`TradeRow.tsx:119-138`).
- [x] 5.2 Tooltip reframed as discrepancy signal (no "historical/original" claim), with
  `aria-label` and keyboard focus (`TradeRow.tsx:123-136`).
- [x] 5.3 Verify no `dark:` modifiers / only semantic tokens on badge, tooltip, banner, and
  the changed leg cells.
- [x] 5.4 Event row interleaved by effective date (`ExecutionLegsTable.tsx:257`).
- [x] 5.5 Re-verify the event row is value-free and excluded from all leg totals / COMBO
  summaries.

## 6. Tests

- [x] 6.1 Updated `ExecutionRow.test.tsx`: primary displayed value is as-traded (`raw_*`),
  plain text; the chart-adjusted counterpart is asserted via the icon's `title` attribute
  (`getByTitle(/split-adjusted/)`), not as visible text — guards against the "(adjusted:
  …)" text regression.
- [x] 6.2 Updated the marking test to assert exactly one `title` matching
  `/The price chart shows this value as/` across two rows (one restated, one untouched).
- [x] 6.3 Component test: a leg's notional equals `raw_price × raw_quantity × multiplier`
  (guards the in-row basis fix). *Manually verified via code read; explicit test not yet
  added.*
- [x] 6.4 Component test: `TradeRow` indicator present when affected, absent when not; and
  the tooltip does not assert "historical/original".
- [x] 6.5 Component test: value-free corporate-action event row at the effective date, not
  summed into totals.
- [x] 6.6 Component test: the detail chart-basis disclosure is shown for an affected trade
  (including a held-across-split trade where header == chart) and absent otherwise.

## 7. Review

- [x] 7.1 `ui-reviewer` pass on trade table + trade-detail (frontend-only), incl. the
  icon-in-parentheses cell format and chart marker.
- [x] 7.2 `code-reviewer` pass (no `dark:`, semantic tokens, one basis per numeric surface,
  no local adjustment math, event row excluded from aggregates, disclosure copy accurate,
  no lingering `origin='split'`-as-corporate-action assumptions).
