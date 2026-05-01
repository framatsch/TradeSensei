## Why

The application currently lacks a clear architectural separation between analytical and operational workflows. The Trading Log page renders a data table without a dedicated sidebar for I/O actions and saved filter shortcuts, while the Portfolio Workspace and Daily Check-in Hub require cleaner pillar-based routing and navigation. This change implements the Pillar Architecture — three distinct UI pillars (Portfolio Workspace, Trading Log, Market Check-in), each optimized for its function — and consolidates the Trading Log's actions and saved filters into a single left sidebar command center.

## What Changes

- Introduce a "Pillar" navigation model: three top-level workspaces routed via `/dashboard/workspace/`, `/dashboard/trades/`, and `/dashboard/checkins/`.
- Refactor the Trading Log (`/dashboard/trades`) with a unified left sidebar containing an Actions section (New Trade, Quick Import, CSV Export) and a Saved Filters section (preset + user-saved filters).
- Add a collapsible Filter Configurator panel at the top of the trade table with a "Save Filter" button that persists named filters to the sidebar.
- Update URL-sync for all active filter state (status, dates, search, saved filter selection) for shareability and navigation persistence.
- Dynamically append `SavedDashboardView` entries as sub-links under "Reporting Hub" in the Portfolio Workspace sidebar.
- Enforce "Market Regime" nomenclature throughout the Check-in Hub.
- Decouple `TradingLog` components from heavy charting library imports used in the Reporting Hub.

## Capabilities

### New Capabilities
- `trading-log-operative-sidebar`: Unified left sidebar for the Trading Log pillar — Actions section (New Trade, Quick Import, CSV Export) and Saved Filters section (All Trades, Open Trades, All Winners, All Losers, user-saved filters). Includes filter persistence via Save Filter button.
- `pillar-routing`: Pillar-based routing architecture separating Portfolio Workspace (`/workspace/`), Trading Log (`/trades/`), and Market Check-in (`/checkins/`) into distinct layout contexts.
- `filter-url-sync`: URL parameter synchronization for all active Trade Log filter state (ticker, date range, status, selected saved filter) enabling shareability and back-navigation.

### Modified Capabilities
- `reporting-hub-ui`: Dynamic sub-links under "Reporting Hub" sidebar item — saved views from the `SavedDashboardView` API are appended as child navigation entries.

## Impact

- Frontend routing: new layout files for pillar-scoped navigation (`/dashboard/trades/layout.tsx`, `/dashboard/workspace/layout.tsx`, `/dashboard/checkins/layout.tsx`).
- Sidebar components: new `TradingLogSidebar` component decoupled from charting libraries.
- URL state management: new `useTradeFilterParams` hook or similar for syncing filters to/from URL search params.
- Existing `/dashboard/trades` page refactored — sidebar replaced, filter bar made collapsible, pagination footer added.
- `SavedDashboardView` API integration added to the Reporting Hub sidebar.
