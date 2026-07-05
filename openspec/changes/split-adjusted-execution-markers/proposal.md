## Why

Historical trade execution markers no longer align with the price chart after a stock
split. The Market Data Hub (LSEG) returns OHLCV bars **only in the current,
split-adjusted price space**, but stored executions (`LogicalExecution` /
`BrokerRawTransaction`) keep the **original raw broker prices** from before the split.
A pre-split buy recorded at 500 € therefore floats far above a chart that now trades
around 50 € after a 10:1 split, making old trades unreadable. Users need execution
markers rendered in the same (adjusted) price space as the chart, while still seeing the
original raw values they entered.

## What Changes

- Add a backend **adjusted execution layer** in `ExecutionService` that computes
  split-adjusted `price`/`quantity` per leg on-the-fly from the user's
  `CorporateAction` records (`price ÷ ratio`, `quantity × ratio`, applied for every
  split dated after the execution).
- Extend the executions API response so every leg carries **both** value pairs:
  adjusted (`price`, `quantity` — aligned to the chart) and raw
  (`raw_price`, `raw_quantity` — the originally stored broker/manual values).
- Update the trade chart UI to render markers at the **adjusted** price and label them
  with both values in parallel — e.g. `50 € (raw: 500 €)` — so no user toggle is
  required and the markers always sit correctly on the chart.
- Legs with `origin='manual'` (no backing `BrokerRawTransaction` and no relevant
  `CorporateAction`) fall back to their stored values: adjusted == raw.
- Ensure aggregate figures shown alongside markers (per-leg P&L, commission) remain
  mathematically consistent between the raw and adjusted representations.

Explicitly **out of scope**:
- No change to the OHLCV / Market Data Hub fetch path — the chart is already always
  adjusted; there is no "unadjusted bars" request to build.
- No new `?mode=raw` chart request and no persistence of adjusted values back onto
  `LogicalExecution` or `BrokerRawTransaction` rows (both remain the raw source of truth).

## Capabilities

### New Capabilities
- `split-adjusted-execution-markers`: On-the-fly split adjustment of execution legs for
  chart alignment, exposing both adjusted and raw price/quantity pairs via the
  executions API and rendering them together in the trade chart UI.

### Modified Capabilities
<!-- None. Existing execution/chart specs keep their current requirements; this adds a
     new derived view rather than changing existing behavior. -->

## Impact

- **Backend**
  - `app/services/execution.py` (`ExecutionService.list_for_trade`) — new optional
    adjusted computation path.
  - `app/services/corporate_action_service.py` — reuse `list_for_aggregator` to load
    per-user `CorporateAction` records.
  - `app/schemas/execution.py` (`LogicalExecutionRead`) — add `raw_price`,
    `raw_quantity` fields (adjusted values stay in existing `price`/`quantity`).
  - `app/api/v1/executions.py` — `list_trade_executions` returns the enriched schema
    (no new required query param; adjustment applied by default).
  - Reference for split math: `app/utils/parsers/aggregator.py:677` (`_apply_split_event`).
- **Frontend**
  - Trade chart marker component — display `adjusted (raw: …)` label; regenerate the
    OpenAPI client after schema change (`/openapi-sync`).
- **APIs**: `GET /portfolios/{portfolio_id}/trades/{trade_id}/executions` response gains
  two fields. Additive, non-breaking for existing consumers.
- **Data model / migrations**: none — `CorporateAction`, `LogicalExecution`,
  `BrokerRawTransaction` are unchanged.
- **Dependencies / external services**: none — Market Data Hub untouched.
