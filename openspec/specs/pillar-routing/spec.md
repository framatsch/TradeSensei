## MODIFIED Requirements

### Requirement: Three distinct pillar layouts route to isolated workspace contexts
The application SHALL present three distinct "Pillars" — Portfolio Workspace, Trading Log, and Market Check-in — each with a layout optimized for its function. The active pillar SHALL be reflected in the breadcrumb or top bar context label. The Portfolio Workspace pillar SHALL be canonical at `/dashboard/workspace/` and the legacy routes `/dashboard/analytics` and `/dashboard/reporting` SHALL redirect to their workspace equivalents.

#### Scenario: Trading Log pillar isolates operative interface
- **WHEN** the user is on any `/dashboard/trades` route
- **THEN** the layout shows the Trading Log operative sidebar (Actions + Saved Filters)
- **AND** the global navigation sidebar is NOT shown

#### Scenario: Portfolio Workspace pillar shows analytics navigation
- **WHEN** the user is on any `/dashboard/workspace` route
- **THEN** the layout shows the Portfolio Workspace sidebar with ANALYTICS, REPORTING, and PERFORMANCE sections
- **AND** the sidebar includes: Overview, Calendar (Analytics), Reporting Hub (Reporting), Strategy, Behavior (Performance)

#### Scenario: Legacy analytics route redirects to workspace
- **WHEN** the user navigates to `/dashboard/analytics`
- **THEN** they are redirected to `/dashboard/workspace/performance/strategy`

#### Scenario: Legacy reporting route redirects to workspace
- **WHEN** the user navigates to `/dashboard/reporting`
- **THEN** they are redirected to `/dashboard/workspace/reporting`
