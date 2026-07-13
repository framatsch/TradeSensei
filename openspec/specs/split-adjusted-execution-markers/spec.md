# split-adjusted-execution-markers Specification

## Purpose

Execution markers on the trade chart must align with the always split-adjusted OHLCV
series. This capability computes split-adjusted execution values on-the-fly, exposes both
adjusted and raw values through the executions API, and renders dual-value marker labels
in the UI.

## Requirements

### Requirement: Split-Adjusted Execution Values

The `ExecutionService` SHALL compute split-adjusted `price` and `quantity` for each
execution leg on-the-fly, so that markers align with the always-adjusted OHLCV chart.
Adjustment MUST apply every `CorporateAction` (matched by symbol/conid and dated after
the execution's `executed_at`) as `adjusted_price = raw_price ÷ ∏ratio` and
`adjusted_quantity = raw_quantity × ∏ratio`, using `Decimal` arithmetic throughout.
Stored `LogicalExecution` and `BrokerRawTransaction` rows MUST remain unchanged (raw
source of truth); adjustment is a derived, non-persisted view.

#### Scenario: Execution before a forward split is adjusted
- **WHEN** an execution has `raw_price=500` and `raw_quantity=1` and a 10:1
  `CorporateAction` (ratio `10.0`) exists for the symbol dated after the execution
- **THEN** the service returns `price=50` and `quantity=10` for that leg
- **AND** the persisted `LogicalExecution` row still reads `price=500`, `quantity=1`

#### Scenario: Execution after all splits is unchanged
- **WHEN** an execution's `executed_at` is later than every relevant `CorporateAction`
- **THEN** the returned adjusted `price`/`quantity` equal the raw `price`/`quantity`

#### Scenario: Multiple sequential splits compound
- **WHEN** two forward splits (ratio `2.0` then `5.0`) are both dated after the execution
- **THEN** the adjusted quantity is `raw_quantity × 10` and adjusted price is
  `raw_price ÷ 10`

### Requirement: Executions API Exposes Adjusted and Raw Values

The endpoint `GET /portfolios/{portfolio_id}/trades/{trade_id}/executions` SHALL return
each leg with both value pairs: the split-adjusted values in the existing `price` and
`quantity` fields, and the original stored values in new `raw_price` and `raw_quantity`
fields. The change MUST be additive and non-breaking for existing consumers.

#### Scenario: Response carries both adjusted and raw pairs
- **WHEN** a client requests executions for a trade that precedes a split
- **THEN** each returned leg includes `price`/`quantity` (adjusted) and
  `raw_price`/`raw_quantity` (original), where adjusted differs from raw by the split
  ratio

#### Scenario: No corporate action means adjusted equals raw
- **WHEN** the trade's symbol has no `CorporateAction` records for the relevant period
- **THEN** every leg returns `price == raw_price` and `quantity == raw_quantity`

### Requirement: Manual Execution Fallback

Execution legs with `origin='manual'` that lack a backing `BrokerRawTransaction` and any
applicable `CorporateAction` SHALL fall back to their stored `LogicalExecution` values,
returning `raw_price == price` and `raw_quantity == quantity`. Manual legs MUST still be
adjusted if a relevant `CorporateAction` applies to their symbol and date.

#### Scenario: Manual leg without corporate action
- **WHEN** a leg has `origin='manual'` and no applicable `CorporateAction`
- **THEN** the returned adjusted values equal its stored values and `raw_*` mirror them

#### Scenario: Manual leg with an applicable split
- **WHEN** a manual leg predates a `CorporateAction` for its symbol
- **THEN** its `price`/`quantity` are adjusted by the split ratio while `raw_price`/
  `raw_quantity` retain the originally entered values

### Requirement: Aggregate Consistency Across Representations

Per-leg P&L and commission shown alongside markers SHALL remain mathematically
consistent between raw and adjusted representations: the notional value of a leg
(`price × quantity`) MUST be invariant under split adjustment, and commission MUST NOT be
double-scaled.

#### Scenario: Notional is invariant under adjustment
- **WHEN** a leg is adjusted by any split ratio
- **THEN** `price × quantity` (adjusted) equals `raw_price × raw_quantity` within
  `Decimal` rounding tolerance

### Requirement: Chart Marker Dual-Value Display

The trade chart UI SHALL position execution markers at the adjusted price and label each
marker with both values in parallel, formatted as `<adjusted> (raw: <raw>)`. When
adjusted equals raw, the UI SHALL display only the single value without a redundant
`(raw: …)` suffix.

#### Scenario: Marker on a pre-split trade shows both values
- **WHEN** a marker's adjusted price is `50` and raw price is `500`
- **THEN** the marker is drawn at the `50` price level on the chart
- **AND** its label reads `50 € (raw: 500 €)`

#### Scenario: Marker with no adjustment shows a single value
- **WHEN** a marker's adjusted and raw prices are equal
- **THEN** the label shows only that value with no `(raw: …)` suffix

### Requirement: Test Coverage for Adjusted Execution View

The system SHALL include automated tests verifying adjusted computation, the dual-value
API response, manual-leg fallback, and the UI dual-value rendering.

#### Scenario: Backend test — adjusted values computed from corporate actions
- **WHEN** a pytest exercises `list_for_trade` for a trade preceding a split
- **THEN** it asserts adjusted `price`/`quantity` are scaled and `raw_*` equal the stored
  values

#### Scenario: Backend test — manual fallback
- **WHEN** a pytest exercises a `origin='manual'` leg with no corporate action
- **THEN** it asserts `price == raw_price` and `quantity == raw_quantity`

#### Scenario: Frontend test — dual-value marker label
- **WHEN** a component test renders a marker whose adjusted and raw prices differ
- **THEN** it asserts the label contains both the adjusted value and `(raw: …)`
