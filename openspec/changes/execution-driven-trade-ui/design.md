## Context

The `isolated-raw-layer-architecture` change (complete) introduced three database tables — `BrokerRawTransaction`, `LogicalExecution`, and `TransactionExecutionMapping` — and refactored the aggregator to compute trades exclusively from `LogicalExecution` records. However, no backend API endpoints or Pydantic schemas exist for `LogicalExecution` CRUD, and the frontend remains unaware of the execution layer. The Trade Detail page renders flat aggregated values, the Edit Form allows direct modification of all fields (including what are now computed values), and the `PartialCloseModal` operates at the Trade level instead of creating execution records.

The current frontend components are:
- `TradeDetailPage` (`app/dashboard/trades/[id]/page.tsx`) — 424-line page component with header, chart, flat execution grid, notes, performance sidebar
- `TradeEditForm` (`components/trades/TradeEditForm.tsx`) — 450-line form editing all trade fields including entry_price, quantity, etc.
- `PartialCloseModal` (`components/trades/PartialCloseModal.tsx`) — 176-line modal for partial position closes
- `BulkActionToolbar` (`components/trades/BulkActionToolbar.tsx`) — bulk actions for selected trades
- `TradeRow` (`components/trades/TradeRow.tsx`) — single row in the trade table

The project uses Tailwind CSS with a dual-theme design system (light/dark), React Query for server state, and follows the conventions in `AGENTS.md` (semantic tokens preferred, `bg-card`, `border-border`, `text-foreground`, etc.).

## Goals / Non-Goals

**Goals:**
- Expose execution-level granularity in the Trade Detail page: summary card + expandable legs table
- Provide a modal for adding manual execution legs (BUY/SELL), replacing `PartialCloseModal`
- Support inline editing of existing execution rows (click-to-edit)
- Build the merge workflow: bulk select + detail page entry, preview modal, backend endpoint
- Make position conflicts a first-class UX workflow (banner, badge, filter)
- Restrict the Trade Edit Form to metadata-only fields; computed fields become read-only
- Build backend CRUD endpoints for `LogicalExecution` with automatic trade re-aggregation

**Non-Goals:**
- Exposing raw broker transactions in the main UI (deferred to a feature-toggle debug view)
- Modifying the import flow (already done in `isolated-raw-layer-architecture`)
- Changing the aggregation algorithm or FIFO matching logic
- Building a full "split execution" UI (only delete + re-add as two new executions)
- Mobile-native app — responsive web is sufficient

## Decisions

**1. Execution-Driven Single Source of Truth**
- *Decision*: Trade-level fields `quantity`, `entry_price`, `exit_price`, `pnl`, `net_pnl`, `commission`, `opened_at`, `closed_at` are always computed from `LogicalExecution` records. The Edit Form renders them read-only.
- *Rationale*: This is the entire point of the two-layer architecture. Dual-editing (direct on Trade + via executions) would create conflicting state and re-import confusion. A single source of truth eliminates an entire class of bugs.
- *Alternative*: "Smart hybrid" with unlock-to-override toggles — rejected because it reintroduces dual source of truth and doubles the complexity of the edit form state.

**2. Modal Dialog for Adding Executions**
- *Decision*: Adding an execution opens a modal dialog with a BUY/SELL segmented toggle, quantity, price, date, commission, and optional P&L fields.
- *Rationale*: Adding executions is an infrequent action (1-3 per trade lifecycle). A modal provides focused form state, clean validation, and mobile-friendly behavior (full-width on small viewports). The codebase already uses this pattern (`PartialCloseModal`), so the interaction is familiar.
- *Alternative A*: Inline form row in the execution table — rejected because it's cramped on mobile and inline validation UX is poor.
- *Alternative B*: Collapsible section below the table — rejected because it permanently consumes page real-estate for an infrequent action.

**3. Both Entry Points for Merge**
- *Decision*: Users can merge trades from both (a) the trade list via bulk-select checkboxes and a "Merge" button in `BulkActionToolbar`, and (b) the Trade Detail page via a "Merge with..." option in an overflow menu that opens a trade picker.
- *Rationale*: These serve different user intents. Bulk-select is natural when the user is scanning the list and spots two related trades. "Merge with..." is natural when the user is reviewing a specific trade and realizes it should be combined with another.
- *Alternative*: Only one entry point — rejected because both workflows are genuinely common for traders who scale into positions across multiple days.

**4. Conflict Banner + Badge + System Filter (Three-Layer Visibility)**
- *Decision*: When `trade.has_conflict === true`: (a) an amber ⚠ badge appears on the trade row in the list, (b) a prominent amber banner appears at the top of the Trade Detail page with resolution guidance, (c) a system-level "Needs Review" saved filter is added to the sidebar.
- *Rationale*: Conflicts are critical data integrity issues. A badge-only approach risks being overlooked. A banner-only approach requires the user to navigate to each trade. The saved filter provides a workflow entry point for batch-reviewing all conflicts.

**5. Automatic Re-Aggregation on Execution Mutation**
- *Decision*: Every POST/PATCH/DELETE on a `LogicalExecution` triggers re-aggregation of the parent trade. The API returns the updated `TradeRead` alongside the execution response.
- *Rationale*: The user expects immediate feedback when they add/edit/remove an execution. Deferring aggregation to a background job would create a confusing stale-data window.
- *Alternative*: Client-side optimistic calculation — rejected because the aggregation logic (FIFO matching, VWAP, commission allocation) is complex and must match the backend.

**6. PartialCloseModal Replacement (Not Coexistence)**
- *Decision*: `PartialCloseModal` is deleted and fully replaced by `AddExecutionModal`. Closing part of a position = adding a SELL execution.
- *Rationale*: Two modals for conceptually the same operation (reducing position size) creates confusion. The execution-based approach is strictly more powerful (handles entries too) and aligns with the data model.
- *Migration*: The `usePartialCloseTrade` hook is deprecated. The new `useCreateExecution` hook replaces it. The frontend removes all `PartialCloseModal` imports.

**7. Component Architecture**
- *Decision*: Extract execution-related UI into small, focused components following the existing pattern:
  - `ExecutionSummaryCard` — pure display, receives computed values as props
  - `ExecutionLegsTable` — data-fetching wrapper with React Query, delegates to `ExecutionRow`
  - `ExecutionRow` — single row with click-to-edit inline functionality
  - `AddExecutionModal` — controlled modal with form state
  - `MergePreviewModal` — preview display + confirm action
  - `ConflictBanner` — pure display, receives `has_conflict` + resolution hints
  - `ExecutionStatusBadge` — tiny reusable badge component
- *Rationale*: Small components are testable, reusable, and align with the project's existing component granularity (see `TagBadge`, `Spinner`, `MetricHelpLink` patterns).

**8. Backend Router Structure**
- *Decision*: New `app/api/v1/executions.py` router for execution CRUD. Execution listing is nested under trades (`GET /trades/{id}/executions`) but mutation endpoints are flat (`PATCH /executions/{id}`, `DELETE /executions/{id}`). Merge is at `POST /trades/merge`.
- *Rationale*: Listing executions is always in the context of a trade (you don't list all executions globally). But updating/deleting an execution by ID doesn't need the trade context in the URL — the execution ID is globally unique.

## Risks / Trade-offs

- **Risk: Re-aggregation Performance** → The aggregator re-runs on every execution mutation. For trades with many executions (50+), this could be slow. *Mitigation*: The aggregator already handles this (it's the same code that runs on import). Add a `select_for_update` lock on the trade row to prevent concurrent re-aggregation races.

- **Risk: Edit Form UX Regression** → Users who are used to editing entry_price directly will now need to edit the execution row instead. *Mitigation*: Clear "ℹ Computed from executions" hint text with a link to the execution table. Inline click-to-edit on execution rows makes the edit path only one more click.

- **Risk: Merge Data Loss** → Merging trades reassigns executions and deletes the empty source trades. This loses trade-level metadata (notes, tags, playbook) from the non-surviving trade. *Mitigation*: The merge preview modal clearly warns about this. Backend preserves metadata from the first (oldest) trade. Notes from other trades are appended.

- **Risk: Manual Trades Without Executions** → Trades created manually via the "New Trade" form currently don't have `LogicalExecution` records. *Mitigation*: The "New Trade" flow must auto-create a single `LogicalExecution` with `status: manual`. This is a required backend change.

- **Trade-off: PartialClose Migration** → Deleting `PartialCloseModal` removes a working feature during development. *Mitigation*: Implement `AddExecutionModal` first, verify it works, then delete `PartialCloseModal` in the same PR.

## Open Questions

1. **Should the "New Trade" form also become execution-driven?** Currently it creates a Trade directly. In the new model, it should create a Trade + at least one LogicalExecution. This is a required change but the UX for it needs design (either auto-create from the existing fields, or move to an execution-first form).
   - *Proposed resolution*: Keep the existing "New Trade" form as-is but have the backend auto-create a `LogicalExecution` with `status: manual` from the trade's entry fields on creation.

2. **Execution-level P&L display**: Should each execution row show its individual P&L (from the broker), or should P&L only be shown at the trade level?
   - *Proposed resolution*: Show broker-reported P&L on closing execution legs where available. Show "—" for opening legs. This matches the `LogicalExecution.pnl` field semantics.
