# corporate-action-ui-disclosure Specification

## ADDED Requirements

### Requirement: One Value Basis Across the Numeric Journal; Only the Chart Is Adjusted

The system SHALL present a single, consistent value basis across every numeric journal
surface — the trade table, the trade-detail header, the Execution Summary, and the
execution-legs table — so that these surfaces never contradict one another and the legs of
a trade visibly reconcile to that trade's header. That basis is the persisted / as-traded
basis produced by the corporate-action-lifecycle capability (the `Trade` header fields and
each leg's `raw_*` values), NOT the chart-adjusted basis.

The price chart is the single exception: it SHALL remain on the provider-adjusted basis,
because its OHLCV axis is always split-adjusted. Chart execution markers therefore continue
to sit at the adjusted price and MAY show the raw value alongside, per the existing
split-adjusted-execution-markers capability. No other surface SHALL introduce a third basis,
and no numeric journal surface SHALL silently mix bases within one view.

The corporate-action badge and the corporate-action event row exist to explain the *only*
remaining discrepancy this leaves: the numeric journal (as-traded) versus the chart axis
(adjusted). This replaces the previous state in which the execution-legs table showed
adjusted values while the header and summary showed persisted values, so that legs did not
reconcile to the header.

#### Scenario: Journal surfaces agree on one basis

- **WHEN** a trade affected by a corporate action is viewed
- **THEN** the trade table, the detail header, the Execution Summary, and the execution-legs
  table all present the persisted / as-traded basis, and the legs reconcile to the header on
  that basis

#### Scenario: Only the chart diverges, and it is explained

- **WHEN** the same trade is rendered on the price chart
- **THEN** the chart uses the adjusted basis while the numeric surfaces do not, and the
  badge plus the corporate-action event row disclose why the chart differs

#### Scenario: No surface mixes bases within itself

- **WHEN** any single numeric journal surface renders a trade's values (e.g. a leg's price,
  quantity, and derived notional)
- **THEN** all values in that surface are drawn from the same basis, with no cell computed
  from the adjusted basis while its neighbours use the persisted basis

### Requirement: A Single Corporate-Action Icon Is Used Consistently

Every surface that flags corporate-action impact SHALL use one and the same icon, so the
user learns a single visual cue that always means "a corporate action applies here". That
icon is the split-arrow (`Split`), chosen to read as a value splitting into a new one and to
be visually distinct from the execution-splitting vocabulary (`origin='split'`, the "Split"
action and status badge), which is an unrelated feature. The icon SHALL appear on: the
trade-table indicator, the trade-detail corporate-action event row, the per-leg
chart-restatement mark, and the trade-detail chart-basis disclosure. No surface flagging
corporate-action impact SHALL use a different icon for the same meaning.

Each icon instance SHALL carry an accessible label or an adjacent text equivalent, so the
meaning is available to assistive technology and not conveyed by shape alone.

The price chart renders markers via a canvas-drawn shape primitive (not an embeddable icon
glyph). On the chart, the corporate-action cue SHALL be a marker placed at each corporate
action's effective date, using a shape and color distinct from the entry/exit execution
markers and labelled with the action's ratio and date. This is the closest chart-native
equivalent of the shared icon and SHALL only be placed when the effective date falls within
the chart's currently rendered candle range, so it is never clamped to a misleading edge
position.

#### Scenario: The same icon marks every corporate-action surface

- **WHEN** a trade affected by a corporate action is viewed across the table and the detail
  view
- **THEN** the table indicator, the event row, the per-leg mark, and the chart-basis
  disclosure all use the split-arrow icon

#### Scenario: The corporate-action icon is distinct from execution-splitting

- **WHEN** a leg with `origin='split'` (execution splitting) and a corporate-action mark are
  both present
- **THEN** the corporate-action icon is the split-arrow and is not the same glyph used for
  the execution-splitting "Split" action or status badge

#### Scenario: Icon has an accessible label

- **WHEN** the corporate-action icon is rendered without adjacent text
- **THEN** it exposes an accessible label identifying it as a corporate-action indicator

#### Scenario: Chart marker appears at the effective date within the visible range

- **WHEN** a corporate action's effective date falls within the chart's currently rendered
  candle range
- **THEN** a distinct marker is placed at that date, labelled with the action's ratio and
  date

#### Scenario: Chart marker is omitted when outside the visible range

- **WHEN** a corporate action's effective date falls outside the chart's currently rendered
  candle range
- **THEN** no marker is placed for that action, rather than clamping it to the nearest edge
  candle

### Requirement: The Detail View Discloses That Only the Chart Is Adjusted

Because the price chart is the single surface on the adjusted basis while every numeric
surface is on the as-traded basis, the trade-detail view SHALL disclose this to the user
near the chart, so the chart's divergence reads as an explained property rather than an
unexplained contradiction. The disclosure SHALL appear only for a trade actually affected by
a corporate action, and SHALL state that the numeric values are as-traded while the chart is
split-adjusted.

This supersedes the prior detail banner copy ("Trade header values are chart-adjusted;
execution rows display both adjusted and raw values"), which is inconsistent with the
one-basis principle: under this change the header and legs are as-traded, not adjusted. The
disclosure's visibility condition SHALL key off corporate-action impact, not off whether
`quantity` equals `chart_quantity`, so that a trade held across a split (whose header and
chart happen to coincide) is still explained.

#### Scenario: Affected trade discloses the chart basis in the detail view

- **WHEN** a trade with a non-empty `corporate_action_impact` is opened in the detail view
- **THEN** a disclosure near the chart states that the numeric values are as-traded and the
  chart is split-adjusted

#### Scenario: Unaffected trade shows no chart-basis disclosure

- **WHEN** a trade with an empty `corporate_action_impact` is opened
- **THEN** no chart-basis disclosure is shown

#### Scenario: Held-across-split trade is still disclosed

- **WHEN** a trade held across a split — whose as-traded header equals its chart-adjusted
  header — is opened
- **THEN** the disclosure is still shown, because visibility keys off corporate-action
  impact rather than a numeric equality of header and chart values

### Requirement: Trade Table Value Basis Is Documented, Not Changed

The trade table SHALL continue to render each trade's persisted `Trade` values
(`quantity`, `entry_price`, `exit_price`, `pnl`) exactly as the corporate-action-lifecycle
capability produces them. This change SHALL NOT alter which values the table shows; it only
adds disclosure. The persisted values follow the holding-period rule and therefore rest on
one of two bases depending on the trade:

- **Trade fully closed before an action's effective date** — the persisted values are the
  original, as-traded values (raw). Only the price chart restates them (`chart_*`,
  derived on read). The table and the chart legitimately differ for such a trade.
- **Trade held across an action's effective date** — the persisted entry values are
  split-normalised onto the post-action share unit so that entry and exit share one unit
  and realised PnL is correct. The table's `entry_price`/`quantity` therefore differ from
  the originally-traded price/quantity, and the chart-adjusted header equals the table.

The originally-traded values for a held trade remain available on the trade-detail page via
each execution leg's `raw_price`/`raw_quantity`, so no data is lost. This is independent of
a leg's `origin`: `origin='split'` denotes execution splitting (a manual or import-backfill
mechanism unrelated to corporate actions) and MUST NOT be treated as a signal of
corporate-action adjustment.

#### Scenario: Closed-before-split trade keeps raw values in the table

- **WHEN** a trade opened and fully closed before an action's effective date is shown
- **THEN** the table displays its original as-traded `entry_price` and `quantity`, and only
  the chart applies the ratio

#### Scenario: Held-across-split trade shows split-normalised values in the table

- **WHEN** a trade was open across an action's effective date
- **THEN** the table displays the split-normalised `entry_price` and `quantity` (post-action
  share unit), which equal the chart-adjusted header, while the original as-traded values
  remain visible as the trade's execution legs on the detail page

### Requirement: Trade Table Corporate-Action Discrepancy Indicator

The trade table SHALL render a corporate-action indicator adjacent to the ticker symbol of
any trade whose `corporate_action_impact` is non-empty, and SHALL NOT render an indicator
for trades with no corporate-action impact. The indicator is a **discrepancy signal**: it
warns that the trade's numbers may differ across the table, the chart, and the originally
traded values because a corporate action applies. It is not a per-value explainer.

The indicator SHALL expose, via a tooltip on hover or focus, each applicable corporate
action's ratio and effective date, and SHALL direct the user to the trade detail page for
the reconciled per-leg values rather than asserting a single "basis" label for the row. The
tooltip copy SHALL NOT claim the row shows original/as-traded values, because for a
held-across-split trade it does not. The indicator MUST consume the `corporate_action_impact`
already present on the trade read model and MUST NOT trigger an additional data request.

#### Scenario: Affected trade shows the indicator

- **WHEN** a trade's `corporate_action_impact` array contains at least one action
- **THEN** the row renders the indicator next to the ticker, and its tooltip lists each
  action's ratio and effective date and points to the trade detail for reconciled values

#### Scenario: Tooltip does not misstate the basis

- **WHEN** the indicator's tooltip is shown for any affected trade
- **THEN** the tooltip does not assert that the table values are the original as-traded
  values, since a held-across-split trade shows split-normalised values

#### Scenario: Unaffected trade shows no indicator

- **WHEN** a trade's `corporate_action_impact` array is empty
- **THEN** no indicator is rendered on that row

#### Scenario: Tooltip is keyboard-accessible

- **WHEN** a user focuses the indicator via keyboard
- **THEN** the tooltip content is exposed to assistive technology and does not rely on
  pointer hover alone

### Requirement: Corporate Action Event Row in Execution Timeline

The trade-detail execution list SHALL render a derived corporate-action event row for
each action in the trade's `corporate_action_impact`, positioned chronologically among
the execution legs by the action's effective date. The event row is presentation-only: it
SHALL NOT be a `LogicalExecution`, SHALL NOT be persisted, and SHALL NOT display price,
quantity, profit-and-loss, or commission. It SHALL display the action type context
(ratio and effective date) sufficient for the user to locate the split within the trade's
history.

#### Scenario: Event row appears between the surrounding legs

- **WHEN** a trade has a buy leg dated before an action's effective date and a sell leg
  dated after it
- **THEN** the corporate-action event row is rendered between those two legs in
  effective-date order

#### Scenario: Event row carries no financial values

- **WHEN** a corporate-action event row is rendered
- **THEN** it shows no price, quantity, P&L, or commission, and is visually distinct from
  execution legs

#### Scenario: No corporate action means no event row

- **WHEN** a trade's `corporate_action_impact` is empty
- **THEN** no corporate-action event row is rendered in its execution list

### Requirement: Execution Legs Render the As-Traded Basis as the Primary Value

The execution-legs table SHALL render each leg's as-traded values (`raw_price`,
`raw_quantity`) as the primary displayed price and quantity, and every value derived within
that table — notably a leg's notional (`quantity × price × multiplier`) — SHALL be computed
from the same as-traded basis, never partly from the adjusted basis. This aligns the legs
with the trade header and the Execution Summary so the legs reconcile to the header.

The existing behavior in which legs displayed adjusted values by default (with a
`suppressAdjustedValues` fallback only for closed-before-split trades) SHALL be replaced by
the as-traded basis as the uniform default. The chart is unaffected and keeps the adjusted
basis.

A leg's edit inputs already operate on the as-traded (`raw_*`) values; making the display
as-traded SHALL remove the prior mismatch in which a user edited one value while a different
(adjusted) value was shown.

#### Scenario: Leg price and quantity are the as-traded values

- **WHEN** an execution leg is rendered in the legs table
- **THEN** its primary price and quantity are the leg's `raw_price` and `raw_quantity`

#### Scenario: Leg notional uses the as-traded basis

- **WHEN** a leg's notional is displayed
- **THEN** it is computed from the as-traded price and quantity, consistent with the leg's
  displayed price and quantity, and is not computed from the adjusted values

#### Scenario: Legs reconcile to the header

- **WHEN** a trade's legs are summed on the as-traded basis
- **THEN** the result reconciles to the trade header shown in the table and the Execution
  Summary

### Requirement: Adjustment Provenance Is Visible Per Leg

Because a corporate action adjusts a leg only when the position was held across its
effective date, some legs of an affected trade would be restated by the chart and others
would not. The trade-detail view SHALL make this provenance visible per leg, so the user can
see which legs the chart restates, rather than inferring it from mismatched numbers. A leg
whose chart-adjusted value differs from its as-traded value SHALL be distinguishable from a
leg the chart leaves unchanged; a leg with no applicable action SHALL NOT be marked.

Provenance SHALL be derived from the values already available per leg — an adjustment
applies when the leg's adjusted value differs from its as-traded value — and MUST NOT be
recomputed by reapplying ratios in the client.

The provenance mark SHALL be the same shared icon required by "A Single Corporate-Action
Icon Is Used Consistently" above, placed inline next to the restated value in parentheses in
place of a textual "adjusted" label, exposing the concrete adjusted figure via an accessible
label. It SHALL NOT additionally appear as a separate status-column badge for the same leg
— exactly one cue per restated value, not two independent cues (an inline text hint and a
separate icon) for the same fact.

`origin='split'` (execution splitting — see "Execution Legs Render the As-Traded Basis..."
above) is NOT a substitute for this provenance mark and MUST NOT be treated as implying a
leg is chart-restated, nor vice versa; the two are independent and are derived from
unrelated data (leg lineage vs. `price`/`raw_price` divergence).

#### Scenario: Chart-restated leg is marked

- **WHEN** a leg's chart-adjusted value differs from its as-traded value because an action
  applies to it
- **THEN** the leg is visibly marked as chart-restated while its primary displayed value
  remains the as-traded value

#### Scenario: Untouched leg is not marked

- **WHEN** a leg has no applicable corporate action, so its adjusted value equals its
  as-traded value
- **THEN** the leg is not marked and shows a single value

#### Scenario: Provenance distinguishes restated from untouched legs on the same trade

- **WHEN** an affected trade has one leg that predates the effective date (chart-restated)
  and one leg on or after it (untouched)
- **THEN** the view marks the first leg and leaves the second unmarked, and the
  corporate-action event row sits between them at the effective date

#### Scenario: Leg without adjustment shows a single value

- **WHEN** a leg's adjusted price equals its `raw_price`
- **THEN** the row displays only the single value with no `(raw: …)` suffix

### Requirement: Test Coverage for Disclosure UI

The system SHALL include automated component tests verifying the trade-table indicator
visibility (present when affected, absent when not), the presence and value-free nature of
the corporate-action event row, and the per-execution dual-value rendering.

#### Scenario: Component test — indicator visibility

- **WHEN** a test renders a `TradeRow` for a trade with a non-empty
  `corporate_action_impact` and one with an empty array
- **THEN** it asserts the indicator is present in the first and absent in the second

#### Scenario: Component test — event row is value-free

- **WHEN** a test renders the execution list for a trade with a corporate action
- **THEN** it asserts an event row exists at the effective date and contains no price,
  quantity, P&L, or commission

#### Scenario: Component test — dual-value execution row

- **WHEN** a test renders an execution row whose adjusted and raw prices differ
- **THEN** it asserts the row label contains both the adjusted value and `(raw: …)`
