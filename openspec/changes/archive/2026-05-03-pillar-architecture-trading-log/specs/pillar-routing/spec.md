## UI Mockup — Portfolio Workspace Pillar (`/dashboard/reporting`)

```
+---------------------------------------------------------------------------------+
| [ 🍱 ] > PORTFOLIO WORKSPACE                         Portfolio: [ Default ▼ ]   |
+----------------------+----------------------------------------------------------+
| -- ANALYTICS --      |  REPORTING HUB                                           |
| [🏠] Overview        |                                                          |
| [📊] Reporting Hub   |  [ Saved View: Unsaved  ▼ ] [ Save View ]                |
|    • My Monthly      |                                                          |
|    • Strategy A      |  +----------------------------------------------------+  |
|                      |  |              GLOBAL FILTER BAR                     |  |
| -- PERFORMANCE --    |  +----------------------------------------------------+  |
| [🕒] Time            |                                                          |
| [🧩] Strategy        |  [ EQUITY CURVE WIDGET ]      [ WIN RATE WIDGET ]        |
| [🧠] Behavior        |                                                          |
+----------------------+----------------------------------------------------------+
```

**Key layout rules from mockup:**
- Portfolio Workspace uses the existing global sidebar (Analytics + Performance sections)
- Saved dashboard views appear as sub-links under "Reporting Hub" (e.g. "My Monthly", "Strategy A")
- Top bar breadcrumb reads "> PORTFOLIO WORKSPACE" in this pillar

## UI Mockup — Trading Log Pillar (`/dashboard/trades`)

```
+---------------------------------------------------------------------------------+
| [ 🍱 ] > TRADING LOG                                 Portfolio: [ Default ▼ ]   |
+----------------------+----------------------------------------------------------+
| -- ACTIONS --        |  [ ▼ Filter Configuration ]                              |
| [+ ] New Trade       |                                                          |
| [📥] Quick Import    |  [ data table ]                                          |
| [📤] CSV Export      |                                                          |
|                      |  < 1 2 3 >          [ Rows per page: 50 ▼ ]              |
| --    Trades     --  |                                                          |
|    • Open Trades     |                                                          |
|    • All Winners     |                                                          |
|    • All Losers      |                                                          |
+----------------------+----------------------------------------------------------+
```

**Key layout rules:**
- Trading Log uses its OWN sidebar — global sidebar is fully hidden
- Top bar breadcrumb reads "> TRADING LOG"
- Three distinct pillars are navigated via the Bento Menu (`[ 🍱 ]`) in the top bar

## ADDED Requirements

### Requirement: Three distinct pillar layouts route to isolated workspace contexts
The application SHALL present three distinct "Pillars" — Portfolio Workspace, Trading Log, and Market Check-in — each with a layout optimized for its function. The active pillar SHALL be reflected in the breadcrumb or top bar context label.

#### Scenario: Trading Log pillar isolates operative interface
- **WHEN** the user is on any `/dashboard/trades` route
- **THEN** the layout shows the Trading Log operative sidebar (Actions + Saved Filters)
- **AND** the global navigation sidebar is NOT shown

#### Scenario: Portfolio Workspace pillar shows analytics navigation
- **WHEN** the user is on any `/dashboard/workspace` or `/dashboard/reporting` or `/dashboard/analytics` route
- **THEN** the layout shows the Portfolio Workspace sidebar with analytics navigation items

#### Scenario: Market Check-in pillar shows journaling navigation
- **WHEN** the user is on any `/dashboard/checkin` or `/dashboard/checkins` route
- **THEN** the layout shows the Market Check-in navigation

### Requirement: TradingLog components MUST NOT import heavy charting libraries
To maintain high performance in the operative pillar, components used exclusively in the Trading Log SHALL NOT import Recharts, D3, or other heavy charting libraries used in the Reporting Hub.

#### Scenario: Trading Log page loads without charting library bundle
- **WHEN** the user navigates to `/dashboard/trades`
- **THEN** no Recharts or D3 modules are loaded in the page's JavaScript bundle
