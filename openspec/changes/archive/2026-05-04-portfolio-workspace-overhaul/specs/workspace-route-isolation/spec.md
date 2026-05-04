## ADDED Requirements

### Requirement: Workspace routes are isolated under /dashboard/workspace/
The application SHALL provide five isolated routes under `/dashboard/workspace/`: `overview`, `calendar`, `reporting`, `performance/strategy`, and `performance/behavior`. Each route SHALL mount only the components required for that specific view.

#### Scenario: Overview route renders instantly with metric cards and equity curve
- **WHEN** the user navigates to `/dashboard/workspace/overview`
- **THEN** the page renders metric cards (Net P&L, Win Rate, Profit Factor) without waiting for chart data
- **AND** the equity curve chart is lazy-loaded after the initial render

#### Scenario: Calendar route shows P&L heatmap
- **WHEN** the user navigates to `/dashboard/workspace/calendar`
- **THEN** the page renders the P&L calendar heatmap using the existing `Calendar` component
- **AND** no other chart widgets are mounted

#### Scenario: Reporting route shows interactive widget grid with filter bar
- **WHEN** the user navigates to `/dashboard/workspace/reporting`
- **THEN** the page renders the `ReportFilterBar` and the widget grid
- **AND** all Recharts widgets are lazy-loaded via `next/dynamic`

#### Scenario: Strategy route shows scatter plots with circuit breaker
- **WHEN** the user navigates to `/dashboard/workspace/performance/strategy`
- **THEN** the `MaeMfeScatterWidget` and `DurationVsPnlScatterWidget` are lazy-loaded
- **AND** the scatter circuit breaker is active

#### Scenario: Behavior route shows attribution charts with Uncategorized group
- **WHEN** the user navigates to `/dashboard/workspace/performance/behavior`
- **THEN** `PsychologicalAttributionWidget` and `PlaybookPhaseHeatmapWidget` are rendered
- **AND** trades without a linked daily check-in are grouped as "Uncategorized"

### Requirement: Workspace layout renders a persistent sidebar with unified nav
The workspace layout (`app/dashboard/workspace/layout.tsx`) SHALL render a `WorkspaceSidebarNav` component that remains mounted across all child routes. The sidebar SHALL contain three sections: ANALYTICS (Overview, Calendar), REPORTING (Reporting Hub with saved view sub-links), and PERFORMANCE (Time, Strategy, Behavior).

#### Scenario: Sidebar persists when navigating between workspace routes
- **WHEN** the user clicks a sidebar link to navigate between workspace routes
- **THEN** the sidebar component does NOT unmount or re-render
- **AND** only the main content area changes

#### Scenario: Active route is highlighted in the sidebar
- **WHEN** the user is on `/dashboard/workspace/performance/strategy`
- **THEN** the "Strategy" sidebar item is visually active/selected

### Requirement: Global filter state is shared across all workspace routes via context
The workspace layout SHALL provide a `WorkspaceFilterContext` to all child routes. The context SHALL contain the current filter state (`date_from`, `date_to`, `playbook_ids`, `tag_ids`) and a setter. Filter state SHALL be initialized from URL search parameters and persisted to URL on change.

#### Scenario: Filter state persists when navigating between routes
- **WHEN** the user sets a date range in the Reporting route filter bar
- **AND** navigates to the Performance/Strategy route
- **THEN** the same date range is active in the strategy route's queries
- **AND** the URL search parameters are preserved

#### Scenario: Direct URL with filters loads with those filters applied
- **WHEN** the user opens `/dashboard/workspace/reporting?date_from=2026-01-01&date_to=2026-01-31`
- **THEN** the filter bar shows the specified date range
- **AND** all widgets query with those filter parameters

### Requirement: Legacy routes redirect to workspace equivalents
The routes `/dashboard/analytics` and `/dashboard/reporting` SHALL redirect to their workspace equivalents to preserve existing bookmarks.

#### Scenario: Analytics redirect
- **WHEN** the user navigates to `/dashboard/analytics`
- **THEN** they are redirected to `/dashboard/workspace/performance/strategy`

#### Scenario: Reporting redirect
- **WHEN** the user navigates to `/dashboard/reporting`
- **THEN** they are redirected to `/dashboard/workspace/reporting`

### Requirement: Market Phase is renamed to Market Regime in all UI display strings
All user-facing labels, headings, legend entries, and tooltip text that reference "Market Phase" SHALL be updated to display "Market Regime". This applies to attribution widgets and any chart legends.

#### Scenario: Attribution widget shows Market Regime label
- **WHEN** the user views the Behavior route
- **THEN** the attribution chart heading and legend entries use "Market Regime" not "Market Phase"
