## Why

When option combos are imported (IBKR/Schwab), each leg is persisted with only its
underlying symbol and long/short direction — the strike price, expiration date, and
call/put type are discarded because the parser reduces the OCC symbol (e.g.
`QQQ   251003C00712000`) to the bare underlying (`QQQ`) before storing it. As a result,
in the trade detail view a user cannot tell one leg apart from another (only the opaque
broker `conid` distinguishes them), and the chart's option overlay renders nothing for
imported combos. The contract data exists in the source file but never reaches the user.

## What Changes

- Promote **strike**, **expiry**, and **option_type** (call/put) to typed, queryable
  fields on the execution leg model (both `logical_executions` and
  `broker_raw_transactions`), derived from the OCC symbol during import.
- Add a shared OCC-symbol parser (`app/utils/occ.py`) used by both broker parsers and by
  the backfill migration; refactor IBKR's existing `_extract_occ_underlying` to reuse it.
- Backfill the new fields for already-imported option legs by re-deriving them from the
  full OCC symbol still preserved in `raw_data`.
- Return the three fields in the leg API response (`LogicalExecutionRead`).
- Show **Strike**, **Type**, and **Expiry** per leg in the COMBO execution legs table and
  in the per-instrument summary card, so distinct contracts are human-readable (not just
  by `conid`). Contract details live exclusively on the trade detail page (execution legs
  table / summary card) — **not** on the trade chart.

No breaking API changes: all new fields are additive and nullable (non-options and
manually created legs keep `null`).

## Capabilities

### New Capabilities
<!-- None — this extends existing capabilities. -->

### Modified Capabilities
- `combo-positions`: the execution leg model gains typed `strike`/`expiry`/`option_type`
  fields; the COMBO execution legs table and per-instrument summary card display them.

## Descoped

- **Chart-local option overlays** (per-leg strike price lines, option chips, per-leg
  entry/exit markers, expiry vertical line, and the `localStorage`-persisted "Chart
  layers" toggle popover) were implemented in an earlier iteration of this change but
  have been **removed** per explicit product decision: contract details (strike/type/
  expiry) belong on the trade detail page only, not as a chart overlay. The
  `chart-display-settings` capability changes from the original proposal have been
  reverted; `TradeChart.tsx` renders the plain underlying candlestick chart with the
  pre-existing generic entry/exit markers only.

## Impact

- **Backend model**: `backend/app/models/logical_execution.py`,
  `backend/app/models/broker_raw_transaction.py` — three new nullable columns each.
- **Backend schemas**: `backend/app/schemas/broker_raw_transaction.py`,
  `backend/app/schemas/execution.py` — new fields + `option_type` validator.
- **Backend parsers**: `backend/app/utils/parsers/ibkr_xml.py`,
  `backend/app/utils/parsers/schwab_json.py`, new `backend/app/utils/occ.py`.
- **Backend service**: `backend/app/services/logical_execution_service.py` —
  `create_from_raw` copies the new fields.
- **DB migration**: one Alembic revision adding six columns + data backfill from `raw_data`.
- **Frontend**: `frontend/lib/types.ts`, `frontend/components/trades/ExecutionLegsTable.tsx`,
  `frontend/components/trades/ExecutionRow.tsx`,
  `frontend/components/trades/ExecutionSummaryCard.tsx`, and the OpenAPI-generated client
  (`frontend/lib/api/*`) regenerated after backend changes.
  `frontend/components/charts/TradeChart.tsx` was touched to ADD and then REMOVE
  (descoped) the option overlay — no chart-side changes remain in scope.
- **Dependencies**: none new.
