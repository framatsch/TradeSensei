## Why

The Execution Legs section in Trade Details was silently broken: a pending DB migration (`b8d1e4f2a9c3` — simplified execution model) caused every `/executions` API call to return 500, so the table showed "Failed to load executions." with no retry option. Beyond this infrastructure gap, the inline editor only covers `price`, `quantity`, and `commission` — the fields `direction`, `executed_at`, and `pnl` are supported by the backend schema but unreachable from the UI, leaving users unable to correct import errors or manually adjust exit P&L.

## What Changes

- **Error state with retry**: Replace the static "Failed to load executions." text in `ExecutionLegsTable` with a retry button and a diagnostic hint about backend connectivity.
- **Startup migration logging**: Add explicit log output at backend startup that reports migration status (current head, any pending migrations) so future drift is visible in container logs.
- **Direction toggle in inline editor**: Add a LONG / SHORT toggle button to `ExecutionRow` edit mode, submitting `direction` via `PATCH /executions/{id}`.
- **Timestamp picker in inline editor**: Add a datetime-local input for `executed_at` to `ExecutionRow` edit mode.
- **P&L field in inline editor**: Add an optional numeric field for `pnl` in `ExecutionRow` edit mode (visible for all legs, required only for exit legs conceptually — no hard validation).
- **Aggregated fields read-only on Trade**: Remove `pnl`, `net_pnl`, `commission`, `quantity`, `entry_price`, `exit_price`, `opened_at`, `closed_at` from `TradeUpdate` — these are cached/denormalized values always overwritten by re-aggregation. The trade edit form shows them as read-only; they are only changeable via execution legs.

## Capabilities

### New Capabilities
- `execution-leg-editor`: Full inline editing of execution leg fields (`direction`, `executed_at`, `price`, `quantity`, `commission`, `pnl`) with direction toggle and datetime picker, plus an error state with retry in the `ExecutionLegsTable`.

### Modified Capabilities

## Impact

- **Frontend**: `ExecutionRow.tsx` (add direction/datetime/pnl inputs to edit mode), `ExecutionLegsTable.tsx` (error state + retry button), `TradeForm.tsx` (remove aggregated fields from edit mode).
- **Backend**: `app/core/migrations.py` (enhanced startup log), `app/schemas/trade.py` (remove 8 fields from `TradeUpdate`), `app/services/trade_service.py` (shrink `reaggregate_fields`).
- **No new endpoints needed**.
- **BREAKING for API consumers**: `TradeUpdate` no longer accepts `pnl`, `net_pnl`, `commission`, `quantity`, `entry_price`, `exit_price`, `opened_at`, `closed_at`.
