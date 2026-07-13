## Context

An early framing of this feature assumed a raw-vs-adjusted **chart** toggle and that
`LogicalExecution` already stores split-adjusted values. Codebase investigation
disproved both assumptions:

- **OHLCV** is served by a thin proxy to an external Market Data Hub (LSEG,
  `app/api/v1/market_data.py:73`). There is no split-adjustment parameter and no local
  concept of "raw bars". The Hub returns bars **already in current (split-adjusted)
  price space**.
- **Executions** (`LogicalExecution`, `app/models/logical_execution.py:89`; and
  `BrokerRawTransaction`, `app/models/broker_raw_transaction.py:55`) both store **raw**
  broker/manual prices. Split scaling exists only **transiently in the FIFO aggregator**
  (`app/utils/parsers/aggregator.py:677`, `_apply_split_event`: `qty *= ratio`,
  `price /= ratio`) for trade matching, and is never persisted or exposed via the API.

The real problem is a **price-space mismatch**: old execution markers (raw) float
incorrectly over an adjusted chart. The user wants markers rendered in the adjusted price
space with the original values still visible in parallel.

`CorporateAction` (`app/models/corporate_action.py:39`) already stores the per-user
split records (`symbol`, `date`, `ratio`, `old_conid`, `new_conid`) and
`CorporateActionService.list_for_aggregator(user_id)` already loads them.

## Goals / Non-Goals

**Goals:**
- Compute split-adjusted `price`/`quantity` per execution leg on-the-fly for chart
  alignment, using existing `CorporateAction` data and `Decimal` math.
- Expose both adjusted and raw pairs on the executions API (additive, non-breaking).
- Render markers at the adjusted price with a dual-value label `<adjusted> (raw: <raw>)`.
- Correct manual-leg handling: fall back to stored values when no split applies.

**Non-Goals:**
- No change to the Market Data Hub / OHLCV fetch path or cache.
- No `?mode=raw` chart request; no unadjusted-bar retrieval.
- No persistence of adjusted values onto `LogicalExecution` / `BrokerRawTransaction`.
- No user toggle — both values are always shown together.
- No change to the aggregator's internal split handling for trade matching.

## Decisions

### Decision 1: Adjust in a new `ExecutionService` layer (not the aggregator, not the frontend)
Add an adjusted computation path to `ExecutionService.list_for_trade` that loads the
user's `CorporateAction` records and scales each returned leg.

- **Why not reuse the aggregator directly:** the aggregator consumes CAs to match trades
  into open lots (FIFO queues, conid re-keying). Its output is `Trade` matches, not a
  per-leg adjusted view; invoking it here would be a heavy, wrong-shaped dependency.
- **Why not the frontend:** monetary math must use `Decimal` for precision and stay
  consistent with backend aggregates (project rule: `Decimal`, never `float`).
- **Trade-off:** the scaling formula (`price ÷ ratio`, `qty × ratio`) is duplicated in
  spirit from `_apply_split_event`. Kept as a small, independently tested helper rather
  than extracting shared code now, to avoid destabilizing the aggregator. Extraction is a
  possible follow-up if a third consumer appears.

### Decision 2: Scaling formula and matching
For each leg, apply the product of ratios of all `CorporateAction` rows where
`ca.symbol == leg.symbol` (or conid match via `old_conid`/`new_conid`) and
`ca.date > leg.executed_at` (date-only comparison, UTC):
`adjusted_price = raw_price / ∏ratio`, `adjusted_quantity = raw_quantity × ∏ratio`.
Forward split `ratio > 1` lowers price / raises quantity; reverse `ratio < 1` does the
inverse — consistent with the aggregator's semantics.

### Decision 3: Schema shape — additive `raw_*` fields
Extend `LogicalExecutionRead` (`app/schemas/execution.py:208`) with `raw_price: Decimal`
and `raw_quantity: Decimal`. Existing `price`/`quantity` now carry **adjusted** values;
`raw_*` carry the stored originals. Additive and non-breaking; when no split applies,
`raw_*` equal `price`/`quantity`.

- **Alternative considered:** a nested `adjusted: {price, quantity}` object. Rejected —
  larger client churn and breaks the flat shape existing consumers rely on.

### Decision 4: Manual-leg fallback
Legs with `origin='manual'` have no `BrokerRawTransaction`, but the source of `raw_*` is
the `LogicalExecution` row itself (which is always raw), so no special data source is
needed. If a relevant `CorporateAction` exists for the symbol/date, the manual leg is
still adjusted; otherwise adjusted == raw. Fallback is therefore the natural default, not
a special branch.

### Decision 5: UI dual-value rendering
Marker label formats as `<adjusted> (raw: <raw>)`; when adjusted == raw, drop the suffix
to avoid clutter. Marker Y-position uses the adjusted price so it sits on the chart.

## Risks / Trade-offs

- **Missing / incorrect `CorporateAction` records** → markers stay in raw space and
  mismatch the chart. Mitigation: this is a data-entry concern, not a code defect; the
  aggregator already warns on quantity discrepancies suggesting unregistered splits
  (`aggregator.py:443`). No new failure mode introduced.
- **Formula duplication with `_apply_split_event`** → drift risk. Mitigation: shared unit
  tests asserting identical scaling for representative ratios; document the linkage in
  code comments referencing `aggregator.py:677`.
- **conid vs symbol matching after a split** (CAs carry `old_conid`/`new_conid`) →
  mismatched legs if only symbol is compared. Mitigation: match on symbol AND
  conid-in-(old,new); mirror the aggregator's re-keying intent.
- **Per-request CA load cost** → negligible (per-user CA sets are small); load once per
  `list_for_trade` call and reuse across legs.

## Migration Plan

Pure additive change — no DB migration, no data backfill, no external-service change.
1. Backend: add `raw_price`/`raw_quantity` to schema; add adjusted path in service.
2. Regenerate OpenAPI client (`/openapi-sync`).
3. Frontend: consume `raw_*` and render dual-value labels at adjusted Y-position.
Rollback: revert the schema/service/UI commits; no persisted state changes.

## Open Questions

- Should the dual-value label be locale/currency-formatted identically to existing marker
  labels? (Assume yes — reuse the current formatter.) Resolve during frontend implementation.
