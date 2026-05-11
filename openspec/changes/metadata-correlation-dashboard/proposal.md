## Why

Traders who consistently tag their Check-ins (sleep quality, stress, market conditions) and Trades (setup quality, R-Multiple estimates) have no way to visualize whether those annotations correlate. The Reporting Hub currently offers playbook/phase heatmaps but no cross-entity metadata analysis. This change adds a dedicated "Correlation Explorer" page that lets users select any Check-in annotation/taxonomy as X and any Trade annotation/taxonomy as Y, and automatically renders the correct chart type based on the data types involved.

## What Changes

- **New page**: `/dashboard/workspace/correlation` — the Correlation Explorer.
- **New backend endpoint**: `GET /api/v1/analytics/metadata-correlation` — returns correlated (checkin, trade) pairs joined by date, filtered by portfolio/account/date range/base asset, and annotated with resolved values for the selected axes.
- **New chart components**: `ScatterPlotWithRegression`, `BoxAndWhiskerPlot`, `CoOccurrenceHeatmap` — each driven by the correlation endpoint response.
- **KPI bar**: Lightweight aggregate cards (Avg R-Multiple, Win Rate, Max Stress, Max Drawdown %) scoped to the filtered dataset.
- **Raw data table**: Filterable, sortable table of correlated trade+checkin pairs with deep links to trade detail pages.

> **Issue correction — "backend is fully implemented"**: The existing API has taxonomy/annotation CRUD and per-entity assignment endpoints, but **no cross-entity correlation query endpoint exists**. A new backend endpoint is required. This is explicitly flagged because the source issue stated otherwise.

## Capabilities

### New Capabilities

- `metadata-correlation-endpoint`: New `GET /api/v1/analytics/metadata-correlation` endpoint returning correlated (checkin, trade) data pairs with axis values and aggregate KPIs.
- `correlation-explorer-ui`: Frontend page at `/dashboard/workspace/correlation` with global filter bar, KPI cards, axis selectors, dynamic chart (scatter/boxplot/heatmap), and raw data table.

### Modified Capabilities

- `reporting-hub-ui`: Add "Correlation Explorer" as a navigation entry in the Workspace sidebar under the Reporting section.

## Impact

- **Backend**: New service method in `AnalyticsService`, new repository query joining `daily_checkins`, `trades`, `trade_annotations`, `checkin_annotations`, and `annotation_definitions` by date. New Pydantic schemas in `schemas/analytics.py`.
- **Frontend**: New page, new chart components, new React Query hook `useMetadataCorrelation`. Sidebar nav update.
- **OpenAPI client**: Must be regenerated after backend changes.
- **No DB migrations**: Query uses existing tables only.
