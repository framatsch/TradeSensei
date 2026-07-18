# anti-lag-performance Specification

## Purpose
Define performance requirements for workspace charts and data-fetching hooks to avoid UI lag with large datasets.

## Requirements

### Requirement: All Recharts widgets in the workspace are lazy-loaded with next/dynamic
Every component that renders a Recharts chart (`AreaChart`, `ScatterChart`, `BarChart`) SHALL be imported using `next/dynamic` with `{ ssr: false }`. Static imports of Recharts components SHALL NOT exist in any workspace route page file.

#### Scenario: Initial page load does not include Recharts JavaScript
- **WHEN** the user first navigates to any workspace route
- **THEN** the initial HTML render contains only layout and skeleton components
- **AND** Recharts bundle chunks are loaded asynchronously after mount

#### Scenario: Chart skeleton is shown while lazy chunk loads
- **WHEN** a workspace route is mounted and the chart chunk is not yet loaded
- **THEN** the `ChartSkeleton` loading component is displayed in place of the chart

### Requirement: TanStack Query hooks use staleTime of 5 minutes with stable filter-based query keys
All data-fetching hooks used in the workspace (including `useAnalyticsSummary`, `useMarketPhaseCorrelation`, `useReturnDistribution`, `useReportData`) SHALL specify `staleTime: 5 * 60 * 1000`. Query keys SHALL include a stable serialized representation of the active filter configuration.

#### Scenario: Navigation between routes does not trigger redundant network requests
- **WHEN** the user navigates from `/dashboard/workspace/reporting` to `/dashboard/workspace/performance/strategy`
- **AND** the filter configuration has not changed
- **THEN** no new network requests are issued for data already in the cache
- **AND** no loading skeletons are shown for previously loaded data

#### Scenario: Filter change invalidates cache and fetches fresh data
- **WHEN** the user changes the date range in the filter bar
- **THEN** all hooks with the new filter key fetch fresh data
- **AND** loading skeletons are shown during the fetch

### Requirement: Scatter widgets implement a circuit breaker for large raw datasets
`MaeMfeScatterWidget` and `DurationVsPnlScatterWidget` SHALL NOT render a `ScatterChart` when the API response contains more than `SCATTER_MAX_RAW_POINTS` (500) data points. Instead they SHALL render a fallback UI that informs the user to apply narrower filters.

#### Scenario: Circuit breaker activates when data exceeds threshold
- **WHEN** the scatter data API returns more than 500 data points
- **THEN** the `ScatterChart` is NOT rendered
- **AND** a fallback message is shown: "Too many data points to render. Please narrow your date range or apply more filters."

#### Scenario: Scatter chart renders normally below threshold
- **WHEN** the scatter data API returns 500 or fewer data points
- **THEN** the `ScatterChart` renders normally

### Requirement: Filter bar inputs are debounced by at least 300ms before updating URL state
All user inputs in the `ReportFilterBar` and workspace filter bar (date pickers, dropdowns, text inputs) SHALL debounce their effect on the URL search parameters by a minimum of 300ms. Stale in-flight API requests SHALL be cancelled when a new filter value is committed.

#### Scenario: Rapid filter changes do not produce multiple network requests
- **WHEN** the user changes a filter value three times within 300ms
- **THEN** only one network request is issued (for the final value)
- **AND** the URL is updated only after the debounce period

#### Scenario: Changing filter cancels stale in-flight request
- **WHEN** a network request is in flight for filter config A
- **AND** the user changes the filter to config B before the request completes
- **THEN** the request for config A is aborted
- **AND** a new request for config B is issued

### Requirement: Attribution widgets render an Uncategorized group for trades without check-in data
`PsychologicalAttributionWidget` and `PlaybookPhaseHeatmapWidget` SHALL explicitly render a group labeled "Uncategorized" for any trades that do not have an associated daily check-in. These trades SHALL NOT be silently omitted from the chart.

#### Scenario: Uncategorized group appears when trades lack check-in
- **WHEN** the attribution data includes trades without a linked check-in
- **THEN** the chart renders an "Uncategorized" bar or row
- **AND** the P&L contribution of those trades is included in the total

#### Scenario: Uncategorized group is absent when all trades have check-ins
- **WHEN** all trades in the current filter have a linked check-in
- **THEN** no "Uncategorized" group is rendered
