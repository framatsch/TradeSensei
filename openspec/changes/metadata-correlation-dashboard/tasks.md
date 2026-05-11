## 1. Backend — Pydantic Schemas

- [ ] 1.1 Add `MetadataCorrelationDataPoint` schema to `backend/app/schemas/analytics.py`: fields `date: dt.date`, `trade_id: uuid.UUID`, `trade_symbol: str`, `trade_pnl: Decimal`, `x_value: float | str | None`, `x_label: str | None`, `y_value: float | str | None`, `y_label: str | None`
- [ ] 1.2 Add `MetadataCorrelationKPIs` schema: fields `win_rate: Decimal`, `max_drawdown_pct: Decimal`, `matched_count: int`, `total_trades_count: int`
- [ ] 1.3 Add `MetadataCorrelationResponse` schema: fields `kpis: MetadataCorrelationKPIs`, `data_points: list[MetadataCorrelationDataPoint]`, `x_axis_data_type: str`, `y_axis_data_type: str`, `x_axis_name: str`, `y_axis_name: str`
- [ ] 1.4 Add `AxisType = Literal["checkin_annotation", "checkin_taxonomy", "trade_annotation", "trade_taxonomy"]` type alias

## 2. Backend — Repository

- [ ] 2.1 Create `backend/app/repositories/metadata_correlation_repository.py` with async method `get_correlated_pairs(portfolio_id, x_axis_type, x_axis_id, y_axis_type, y_axis_id, date_from, date_to, account_ids, base_asset)` that JOINs `daily_checkins`, `trades`, `trade_annotations`, `checkin_annotations`, and `annotation_definitions` (or taxonomy assignment tables) by date and returns raw rows
- [ ] 2.2 Implement the JOIN for `checkin_annotation` axis type: join `checkin_annotations` filtered by `annotation_definition_id = x_axis_id` to resolve annotation value
- [ ] 2.3 Implement the JOIN for `trade_annotation` axis type: join `trade_annotations` filtered by `annotation_definition_id`
- [ ] 2.4 Implement the JOIN for `checkin_taxonomy` axis type: check existence in `checkin_taxonomy_assignments` table; value is the taxonomy name string
- [ ] 2.5 Implement the JOIN for `trade_taxonomy` axis type: check existence in `trade_taxonomy_assignments`; value is taxonomy name string
- [ ] 2.6 Add `get_filtered_trades_aggregate(portfolio_id, date_from, date_to, account_ids, base_asset)` helper that returns `total_trades_count`, `win_rate`, and `max_drawdown_pct` from `trades` table

## 3. Backend — Service

- [ ] 3.1 Create `backend/app/services/metadata_correlation_service.py` with `MetadataCorrelationService` class
- [ ] 3.2 Implement `get_correlation(...)` method: calls repository, resolves `x_axis_data_type` and `y_axis_data_type` by looking up `AnnotationDefinitionResponse.type` (or `"taxonomy"` for taxonomy axes), calls aggregate helper, assembles `MetadataCorrelationResponse`
- [ ] 3.3 Add scope validation: raise `HTTPException(422)` if `x_axis_type = "checkin_annotation"` but annotation's `scope = "trades"` (and vice-versa)
- [ ] 3.4 Add same-axis validation: raise `HTTPException(422, "X and Y axes must differ")` if `x_axis_id == y_axis_id and x_axis_type == y_axis_type`

## 4. Backend — API Endpoint

- [ ] 4.1 Add route `GET /api/v1/analytics/metadata-correlation` to `backend/app/api/v1/analytics.py` with query params matching `MetadataCorrelationResponse` input, returning `ResponseEnvelope[MetadataCorrelationResponse]`
- [ ] 4.2 Register `MetadataCorrelationService` dependency injection in the route

## 5. OpenAPI Client Sync

- [ ] 5.1 Run `openapi-sync` skill to regenerate `frontend/lib/api/types.gen.ts` and `frontend/lib/api/sdk.gen.ts` after backend endpoint is complete

## 6. Frontend — React Query Hook

- [ ] 6.1 Create `frontend/hooks/useMetadataCorrelation.ts` with `useMetadataCorrelation(params)` hook using the generated SDK client; include `enabled: !!(params.x_axis_id && params.y_axis_id)` guard
- [ ] 6.2 Add `useAnnotationDefinitions` and `useTaxonomies` calls within the page to populate axis dropdowns (both already exist in `hooks/`)

## 7. Frontend — Chart Components

- [ ] 7.1 Create `frontend/components/charts/ScatterWithRegressionChart.tsx`: Recharts `<ScatterChart>` with dots and a `<Line>` for the regression line; compute slope/intercept client-side using simple least-squares; accept `data: {x: number, y: number}[]` and axis label props
- [ ] 7.2 Create `frontend/components/charts/BoxAndWhiskerChart.tsx`: Recharts `<ComposedChart>` with one bar per category showing Q1–Q3 box as a `<Bar>` with custom shape; whiskers via `<ErrorBar>`; outlier dots via `<Scatter>`; accept `data: {category: string, min: number, q1: number, median: number, q3: number, max: number, n: number, outliers: number[]}[]`
- [ ] 7.3 Create `frontend/components/charts/CoOccurrenceHeatmap.tsx`: pure SVG grid rendered via `<ResponsiveContainer>` custom content; cells colored by count using a linear scale from `bg-muted` to `bg-primary`; accept `data: {x_label: string, y_label: string, count: number}[]`
- [ ] 7.4 Create `frontend/components/charts/CorrelationChartRouter.tsx`: wrapper that receives `x_axis_data_type`, `y_axis_data_type`, and `data_points` and renders the appropriate chart component

## 8. Frontend — Correlation Explorer Page

- [ ] 8.1 Create `frontend/app/dashboard/workspace/correlation/page.tsx` with `"use client"` directive
- [ ] 8.2 Implement global filter bar: Period selector (Last 30/90/180/365 days, YTD, custom) and Account selector consuming `useWorkspaceFilter`; Base Asset text input as local state
- [ ] 8.3 Implement KPI cards row: Win Rate, Max Drawdown, Matched/Total (always), Avg Y-Axis and Max X-Axis (conditionally when axes selected and data loaded)
- [ ] 8.4 Implement axis selector section: two grouped `<Select>` dropdowns (X-Axis and Y-Axis) populated from annotation definitions and taxonomies; group labels "Check-in Annotations", "Check-in Taxonomies", "Trade Annotations", "Trade Taxonomies"; show `type` hint in option label
- [ ] 8.5 Integrate `CorrelationChartRouter` below axis selectors; show placeholder when no axes selected; show empty state message when `data_points` is empty with explanation text
- [ ] 8.6 Implement raw data table below chart: columns Date, Symbol (deep link), Y-Value (named), X-Value (named), Win/Loss; search input filtering by symbol; sortable by any column via `useState` sort state
- [ ] 8.7 Add loading skeletons for KPI cards and chart area while `useMetadataCorrelation` is fetching

## 9. Frontend — Sidebar Navigation

- [ ] 9.1 Add "Correlation Explorer" nav link pointing to `/dashboard/workspace/correlation` in the Workspace sidebar component (locate existing sidebar file and add alongside Reporting Hub link)

## 10. Hardening

- [ ] 10.1 Handle box-and-whisker edge case: if a category has N < 3, show the category as a dot/jitter plot instead of a box (or show a tooltip warning)
- [ ] 10.2 Handle regression line edge case: if all X values are identical (zero variance), skip rendering the regression line and show a tooltip "Regression undefined: no variance in X"
- [ ] 10.3 Add `aria-label` to all chart wrappers for accessibility
- [ ] 10.4 Verify the page is responsive: chart and table scroll horizontally on small viewports
