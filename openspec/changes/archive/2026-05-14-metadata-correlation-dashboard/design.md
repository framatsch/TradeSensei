## Context

The existing Reporting Hub (`/dashboard/workspace/reporting`) provides playbook/market-phase performance heatmaps and R-Multiple distribution charts. Traders who tag their Check-ins (e.g., sleep quality 1–10, stress 1–10, market regime as an enum) and Trades (setup quality, notes annotations) with user-defined metadata have no way to visualize cross-entity correlations — e.g., "does poor sleep quality (Check-in annotation) predict lower R-Multiple (Trade annotation)?".

The backend has full taxonomy/annotation CRUD and per-entity assignment. What is missing is:
1. A query that **joins checkins and trades by date** and surfaces their annotation values together.
2. A frontend page that lets the user select arbitrary axes from those annotations and automatically renders the right chart.

## Goals / Non-Goals

**Goals:**
- Build `GET /api/v1/analytics/metadata-correlation` that joins `daily_checkins` × `trades` by date and returns both axis values and aggregate KPIs.
- Build the Correlation Explorer page at `/dashboard/workspace/correlation` with global filter bar, KPI cards, axis selectors, dynamic chart rendering, and raw data table.
- Support three chart modes determined by axis data types: Scatter+Regression (continuous×continuous), Box-and-Whisker (discrete×continuous), Co-occurrence Heatmap (discrete×discrete).
- Handle the **"R-Multiple" case** correctly: R-Multiple is not a system field and may or may not exist as a user-defined float annotation on trades. The UI must not hardcode it — KPI cards and axis dropdowns must be dynamically populated from the user's actual annotation definitions.

**Non-Goals:**
- New DB migrations (uses existing schema).
- Redesigning Trade or Check-in detail views.
- Continuous×discrete (reversed axis order) as a separate mode — same as discrete×continuous, axis labels swap.
- Saving/persisting correlation configurations as saved views (future work).

## Decisions

### D1: New backend endpoint is required
The issue claims the backend is fully implemented. This is incorrect. No cross-entity correlation query exists. We will add:
- `GET /api/v1/analytics/metadata-correlation?portfolio_id=&x_axis_type=checkin_annotation&x_axis_id=<uuid>&y_axis_type=trade_annotation&y_axis_id=<uuid>&date_from=&date_to=&account_ids=`
- Returns: `{ kpis: {...}, data_points: [{date, trade_id, x_value, x_label, y_value, y_label}], x_axis_data_type, y_axis_data_type }`
- Aggregate KPIs are computed server-side from the filtered correlated pairs.

### D2: Chart type selection is driven by annotation `type` field
The `AnnotationDefinitionResponse.type` is `"int" | "float" | "bool" | "string_enum"`. Taxonomy assignments are always discrete (categorical). Chart type is determined as:
- `int` or `float` → continuous
- `bool` or `string_enum` → discrete
- taxonomy → discrete

Frontend type-switch logic:
```
continuous × continuous → ScatterPlotWithRegression
discrete × continuous (or continuous × discrete) → BoxAndWhiskerPlot  
discrete × discrete → CoOccurrenceHeatmap
```

### D3: KPI cards use dynamic annotation definitions, not hardcoded fields
The mockup shows "Avg. R-Multiple", "Winrate", "Max. Stress Level". "Winrate" and "Max Drawdown" are system metrics computed from the filtered trade set. "Avg. R-Multiple" and "Max Stress" depend on user-defined annotations existing with those names. The KPI bar will show:
- Always present: Win Rate (%), Max Drawdown (%) — from trade PnL data
- Conditionally present (if annotation exists with that name): Avg of the selected Y-axis annotation, Max of the selected X-axis annotation
This avoids false assumptions about annotation names.

### D4: Checkin↔Trade linkage is by date
A trade's `opened_at` date is compared to `daily_checkin.date`. Trades with no check-in on that date are excluded from the correlation dataset (null values not plotted). The endpoint includes a `total_trades` vs `matched_trades` count so the UI can show "X/Y trades have linked check-ins".

### D5: Recharts for all chart types
Recharts is the existing library. All three chart types will be implemented using Recharts primitives:
- Scatter: `<ScatterChart>` with a `<ReferenceLine>` for regression (computed client-side with simple linear regression)
- Box-and-Whisker: custom `<ComposedChart>` using `<Bar>` for IQR boxes and `<ErrorBar>` for whiskers
- Heatmap: custom cell grid using `<ResponsiveContainer>` + SVG `<rect>` elements (Recharts has no native heatmap)

### D6: "Account" filter in global bar
The mockup shows `[Konto: Live]`. This maps to `account_ids` filter (existing workspace filter context). The Correlation Explorer will consume `useWorkspaceFilter` from the existing `WorkspaceFilterContext`.

## Risks / Trade-offs

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Users have no checkins linked to trades | Medium | Show empty state with explanation ("No check-ins found for these trade dates") |
| R-Multiple annotation doesn't exist | High | KPIs are dynamic — only show "Avg Y-Axis" not hardcoded "Avg R-Multiple" |
| Large datasets slow the endpoint | Low | Limit to 500 pairs; add `limit` param; show pagination in table |
| Box-and-Whisker with small N per category | Medium | Show N label per box; suppress chart if any category has N < 3 |
| Regression line with collinear data | Low | Catch division-by-zero in client-side regression; omit line if undefined |
| `bool` annotations render poorly as scatter X | Low | Type-switch routes bool to discrete → triggers box-and-whisker automatically |

## UI Mockup

```
┌─────────────────────────────────────────────────────────────────────┐
│  CORRELATION EXPLORER                                               │
│  Period: [Last 90 Days ▼]  Asset: [All ▼]  Account: [Live ▼]       │
├─────────────────────────────────────────────────────────────────────┤
│  [Win Rate: 54%]  [Max Drawdown: 2.4%]  [Avg Y-Axis: 1.42]  [N Matched: 47/82] │
├─────────────────────────────────────────────────────────────────────┤
│  ANALYSIS CONFIGURATION                                             │
│  X-Axis (Cause / Check-in): [Annotation: Sleep Quality (1-10) ▼]   │
│  Y-Axis (Effect / Trade):   [Annotation: R-Multiple (float) ▼]     │
│                          [▶ Run Correlation]                        │
├─────────────────────────────────────────────────────────────────────┤
│  VISUALIZATION  (auto: Scatter — continuous × continuous)           │
│                                                                     │
│  R-Mult ▲                                                           │
│    5.0  │           ·                                               │
│    2.5  │    ·   ·    ·  ────── (regression)                       │
│    0.0  ├──·──·──·──·──────────────────►                           │
│   -1.0  │·  ·              Sleep Quality (1–10)                     │
│         └────────────────────────────────                           │
├─────────────────────────────────────────────────────────────────────┤
│  RAW DATA TABLE (47 correlated pairs)                               │
│  [Search…]  [Sort by Date ▼]                                        │
│  Date       Trade ↗  Y-Value  X-Value  Win/Loss                    │
│  2026-04-12  AAPL  →   2.1     7        Win                        │
│  2026-04-10  TSLA  →  -0.5     4        Loss                       │
└─────────────────────────────────────────────────────────────────────┘
```

Discrete × Discrete mode (Taxonomy × Taxonomy) switches to Co-occurrence Heatmap:
```
              [FOMO]  [Early Exit]  [On-Plan]
[Poor Sleep]    12        3             1
[News Event]     5        5             8
[High Stress]   10        7             2
(cells colored by intensity: green=high co-occurrence, red=low)
```

Discrete × Continuous mode (Taxonomy × float Annotation) switches to Box-and-Whisker:
```
R-Multiple ▲
           │  ┌──┐       ┌──┐
    2.5    │  │  │       │  │
           │  ├──┤  ┌──┐ ├──┤
    1.0    │  │▓▓│  │▓▓│ │▓▓│
           │  ├──┤  ├──┤ ├──┤
    0.0  ──┼──┴──┴──┴──┴─┴──┴──►
           │ FOMO  News  Plan
```
