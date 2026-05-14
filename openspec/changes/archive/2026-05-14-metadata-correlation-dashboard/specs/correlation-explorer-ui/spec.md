## ADDED Requirements

### Requirement: Correlation Explorer page exists at /dashboard/workspace/correlation

The system SHALL render a page at `/dashboard/workspace/correlation` within the Portfolio Workspace layout. The page SHALL be accessible from the Workspace sidebar.

#### Scenario: Page renders with empty state before axes are configured
- **GIVEN** the user navigates to `/dashboard/workspace/correlation`
- **THEN** the global filter bar is visible with Period, Asset, and Account selectors
- **AND** the axis selector section is visible with X-Axis and Y-Axis dropdowns (unpopulated)
- **AND** the chart area shows a placeholder: "Select axes above to visualize correlations"
- **AND** the KPI cards show skeleton/dash placeholders

### Requirement: Global filter bar drives all downstream components

The Correlation Explorer page SHALL use the existing `WorkspaceFilterContext` for `date_from`, `date_to`, and `account_ids`. A local "Base Asset" filter (free-text or dropdown) SHALL be scoped to this page only.

#### Scenario: Changing date range triggers re-fetch
- **WHEN** the user changes the period selector
- **THEN** KPI cards, chart, and data table all re-fetch using the new date range

### Requirement: Axis selectors populate from annotation definitions and taxonomies

The X-Axis and Y-Axis dropdowns SHALL be populated from:
1. All non-archived `AnnotationDefinitionResponse` with `scope` matching the axis side (`checkins` or `trades` or `both`), grouped by side.
2. All non-archived `TaxonomyResponse` with `scope` matching the axis side, grouped by side.

The dropdown SHALL show: `[Check-in Annotations] Sleep Quality (float)`, `[Trade Annotations] Setup Quality (int)`, `[Check-in Taxonomies] Poor Sleep`, etc.

#### Scenario: Annotations and taxonomies are grouped in dropdown
- **WHEN** the user opens the X-Axis dropdown
- **THEN** options are grouped under "Check-in Annotations" and "Check-in Taxonomies"
- **AND** each annotation shows its `type` as a hint (e.g., "int", "float", "string_enum")

#### Scenario: Empty dropdown when no annotations/taxonomies exist
- **WHEN** the user has no check-in annotations defined
- **THEN** the X-Axis dropdown shows "No check-in annotations defined" as a disabled option
- **AND** a link to the metadata library is shown

### Requirement: Chart type is determined automatically from axis data types

After the user selects both axes and the data loads, the chart SHALL automatically render based on the combination of `x_axis_data_type` and `y_axis_data_type` from the API response:

| X type | Y type | Chart |
|--------|--------|-------|
| float or int | float or int | Scatter plot with linear regression line |
| taxonomy or bool or string_enum | float or int | Box-and-Whisker plot |
| float or int | taxonomy or bool or string_enum | Box-and-Whisker plot (axes swapped) |
| taxonomy or bool or string_enum | taxonomy or bool or string_enum | Co-occurrence Heatmap |

#### Scenario: Scatter plot renders for two float annotations
- **GIVEN** X is "Sleep Quality (float)" and Y is "R-Multiple (float)"
- **WHEN** data loads
- **THEN** a scatter plot renders with each data point as a dot
- **AND** a linear regression line is overlaid
- **AND** axis labels show the annotation names

#### Scenario: Box-and-Whisker renders for taxonomy × float
- **GIVEN** X is "Check-in Taxonomy" (discrete) and Y is "R-Multiple (float)"
- **WHEN** data loads
- **THEN** one box is rendered per unique taxonomy label
- **AND** each box shows Q1, median, Q3, whiskers, and outlier dots
- **AND** the N count is shown under each box

#### Scenario: Co-occurrence heatmap renders for two taxonomy axes
- **GIVEN** X and Y are both taxonomy types
- **WHEN** data loads
- **THEN** a matrix grid renders with X labels as columns and Y labels as rows
- **AND** each cell shows the co-occurrence count
- **AND** cell color intensity reflects count magnitude (low=muted, high=accent color)

#### Scenario: Empty state for no matched pairs
- **WHEN** `data_points` is empty
- **THEN** the chart area shows: "No correlated data found. Trades on these dates have no linked check-ins."
- **AND** the KPI card shows `N Matched: 0 / N Total`

### Requirement: KPI cards display system metrics and axis-derived metrics

The KPI bar SHALL always show:
- **Win Rate** — from `kpis.win_rate` (as percentage)
- **Max Drawdown** — from `kpis.max_drawdown_pct` (as percentage)
- **Matched / Total** — `kpis.matched_count / kpis.total_trades_count`

When axes are selected:
- **Avg Y-Axis** — average of `y_value` across all matched data points (labeled with the Y-axis annotation name, e.g., "Avg R-Multiple")
- **Max X-Axis** — max of `x_value` (labeled with X-axis name, e.g., "Max Sleep Quality") — only shown if X is numeric

#### Scenario: KPIs show correctly when data loaded
- **GIVEN** 47 matched pairs with Y-axis "R-Multiple"
- **THEN** the KPI card "Avg R-Multiple" shows the computed mean
- **AND** "Matched / Total" shows "47 / 82"

### Requirement: Raw data table shows correlated pairs

Below the chart, a table SHALL display all data points from the API response with columns: Date, Trade (symbol, deep link to `/dashboard/trades/<id>`), Y-Value (named after axis), X-Value (named after axis), Win/Loss.

The table SHALL support:
- Full-text search filtering by symbol
- Column sorting (click header)
- A "No data" empty state

#### Scenario: Deep link navigates to trade detail
- **WHEN** the user clicks a trade symbol in the table
- **THEN** the browser navigates to `/dashboard/trades/<trade_id>`
