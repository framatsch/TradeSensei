## UI Mockup

```
| [📊] Reporting Hub   |
|    • My Monthly      |
|    • Strategy A      |
```

Saved `SavedDashboardView` entries appear as indented sub-links directly below the "Reporting Hub"
sidebar item. The number of sub-links is dynamic — one per saved view.

## MODIFIED Requirements

### Requirement: Reporting Hub sidebar shows saved views as dynamic sub-links
The Portfolio Workspace sidebar SHALL dynamically append `SavedDashboardView` entries as sub-links under the "Reporting Hub" navigation item. Each sub-link SHALL navigate to `/dashboard/reporting?view_id=<id>`. Sub-links SHALL only appear after the user has created at least one saved view.

#### Scenario: Saved views appear as sub-links under Reporting Hub
- **WHEN** the user has at least one `SavedDashboardView`
- **THEN** the sidebar shows them as clickable sub-links below the "Reporting Hub" item

#### Scenario: Clicking a saved view sub-link loads that view
- **WHEN** the user clicks a saved view sub-link (e.g. "My Monthly")
- **THEN** the browser navigates to `/dashboard/reporting?view_id=<id>`
- **AND** the Reporting Hub loads the corresponding saved view configuration

#### Scenario: No sub-links when no saved views exist
- **WHEN** the user has no saved dashboard views
- **THEN** no sub-links are shown under Reporting Hub in the sidebar
