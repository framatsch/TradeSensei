## Why

The `isolated-raw-layer-architecture` change introduced a two-layer data model (`BrokerRawTransaction` → `LogicalExecution` → `Trade`) but the UI still treats trades as flat, monolithic records. The Trade Detail page shows a single aggregated entry/exit price, the Edit Form allows direct modification of computed fields (creating dual-source-of-truth issues), and there is no way to view, add, edit, or merge individual execution legs. Users cannot scale out of positions at the execution level, cannot merge related trades whose executions were imported separately, and have no visibility into position conflicts flagged by the aggregator. The existing `PartialCloseModal` also operates at the Trade level rather than creating proper `LogicalExecution` records.

## What Changes

- **Replace flat Execution Details** with a computed Summary Card (VWAP entry, total qty, commission) plus a collapsible Execution Legs table showing each `LogicalExecution` with status badges (`imported`, `manual`, `merged`, `split`).
- **Add Execution Modal** replaces `PartialCloseModal`. A unified modal with BUY/SELL toggle for adding entry or exit execution legs to any trade. Creates `LogicalExecution` records with `status: manual`.
- **Execution CRUD API** — new backend endpoints for listing, creating, updating, and deleting `LogicalExecution` records under a trade, with automatic re-aggregation of the parent trade after mutations.
- **Trade Merge workflow** — merge 2+ trades (same symbol/account) into one by reassigning their executions. Entry from both the trade list (bulk select) and trade detail page (picker). Preview modal shows the combined result before confirming.
- **Conflict resolution workflow** — amber conflict banner on Trade Detail when `has_conflict` is true, warning badge on trade rows, and a system-level "Needs Review" saved filter.
- **Edit Form scope reduction** — computed fields (quantity, entry price, exit price, PnL, commission) become read-only in the Trade Edit Form. Only metadata fields remain editable: stop loss, take profit, tags, playbook, notes, TradingView link.
- **Delete `PartialCloseModal`** — all its functionality is absorbed by the new Add Execution Modal.

## Capabilities

### New Capabilities
- `execution-legs-display`: Trade Detail page components for displaying the computed execution summary and the collapsible execution legs table with status badges and inline edit.
- `execution-crud-api`: Backend API endpoints (`GET/POST /trades/{id}/executions`, `PATCH/DELETE /executions/{id}`) with Pydantic schemas, re-aggregation trigger, and frontend hooks/types.
- `add-execution-modal`: Modal dialog for creating manual execution legs (BUY/SELL toggle, qty, price, date, commission) — replaces `PartialCloseModal`.
- `trade-merge`: Merge workflow including backend merge endpoint (`POST /trades/merge`), bulk-select merge from trade list, "Merge with..." from detail page, and preview modal.
- `conflict-resolution-ui`: Conflict banner on detail page, warning badge on trade rows, "Needs Review" system filter, and backend filter support for `has_conflict`.
- `edit-form-execution-driven`: Refactored Trade Edit Form with computed fields rendered read-only and metadata-only editing scope.

### Modified Capabilities
- `trade-import`: The import flow already creates `LogicalExecution` records (done in `isolated-raw-layer-architecture`). No spec changes needed, but the UI now displays execution legs that originate from imports.

## Impact

- **Frontend Components**: 8 new components, 5 modified, 1 deleted (`PartialCloseModal`). Major changes to `TradeDetailPage`, `TradeEditForm`, `BulkActionToolbar`, `TradeRow`.
- **Backend API**: 5 new endpoints, 3 new Pydantic schemas (`LogicalExecutionRead`, `LogicalExecutionCreate`, `MergeTradesRequest`), new router file `executions.py`.
- **Frontend Types**: New `LogicalExecution`, `LogicalExecutionCreate`, `MergeTradesRequest` TypeScript interfaces in `lib/types.ts`.
- **Frontend Hooks**: New `useExecutions`, `useCreateExecution`, `useUpdateExecution`, `useDeleteExecution`, `useMergeTrades` React Query hooks.
- **Database**: No schema changes (tables already exist from `isolated-raw-layer-architecture`). New system-level saved filter row seeded for "Needs Review".
- **Existing Tests**: `PartialCloseModal` tests must be replaced with `AddExecutionModal` tests.
