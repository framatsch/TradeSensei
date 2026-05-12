## 1. Backend — Pydantic Schemas

- [x] 1.1 Add `MetadataCorrelationDataPoint` schema to `backend/app/schemas/analytics.py`: fields `date: dt.date`, `trade_id: uuid.UUID`, `trade_symbol: str`, `trade_pnl: Decimal`, `x_value: float | str | None`, `x_label: str | None`, `y_value: float | str | None`, `y_label: str | None`
- [x] 1.2 Add `MetadataCorrelationKPIs` schema: fields `win_rate: Decimal`, `max_drawdown_pct: Decimal`, `matched_count: int`, `total_trades_count: int`
- [x] 1.3 Add `MetadataCorrelationResponse` schema: fields `kpis: MetadataCorrelationKPIs`, `data_points: list[MetadataCorrelationDataPoint]`, `x_axis_data_type: str`, `y_axis_data_type: str`, `x_axis_name: str`, `y_axis_name: str`
- [x] 1.4 Add `AxisType = Literal["checkin_annotation", "checkin_taxonomy", "trade_annotation", "trade_taxonomy"]` type alias

## 2. Backend — Repository

- [x] 2.1 Create `backend/app/repositories/metadata_correlation_repository.py` with async method `get_correlated_pairs(portfolio_id, x_axis_type, x_axis_id, y_axis_type, y_axis_id, date_from, date_to, account_ids, base_asset)` that JOINs `daily_checkins`, `trades`, `trade_annotations`, `checkin_annotations`, and `annotation_definitions` (or taxonomy assignment tables) by date and returns raw rows
- [x] 2.2 Implement the JOIN for `checkin_annotation` axis type: join `checkin_annotations` filtered by `annotation_definition_id = x_axis_id` to resolve annotation value
- [x] 2.3 Implement the JOIN for `trade_annotation` axis type: join `trade_annotations` filtered by `annotation_definition_id`
- [x] 2.4 Implement the JOIN for `checkin_taxonomy` axis type: check existence in `checkin_taxonomy_assignments` table; value is the taxonomy name string
- [x] 2.5 Implement the JOIN for `trade_taxonomy` axis type: check existence in `trade_taxonomy_assignments`; value is taxonomy name string
- [x] 2.6 Add `get_filtered_trades_aggregate(portfolio_id, date_from, date_to, account_ids, base_asset)` helper that returns `total_trades_count`, `win_rate`, and `max_drawdown_pct` from `trades` table

## 3. Backend — Service

- [x] 3.1 Create `backend/app/services/metadata_correlation_service.py` with `MetadataCorrelationService` class
- [x] 3.2 Implement `get_correlation(...)` method: calls repository, resolves `x_axis_data_type` and `y_axis_data_type` by looking up `AnnotationDefinitionResponse.type` (or `"taxonomy"` for taxonomy axes), calls aggregate helper, assembles `MetadataCorrelationResponse`
- [x] 3.3 Add scope validation: raise `HTTPException(422)` if `x_axis_type = "checkin_annotation"` but annotation's `scope = "trades"` (and vice-versa)
- [x] 3.4 Add same-axis validation: raise `HTTPException(422, "X and Y axes must differ")` if `x_axis_id == y_axis_id and x_axis_type == y_axis_type`

## 4. Backend — API Endpoint

- [x] 4.1 Add route `GET /api/v1/analytics/metadata-correlation` to `backend/app/api/v1/analytics.py` with query params matching `MetadataCorrelationResponse` input, returning `ResponseEnvelope[MetadataCorrelationResponse]`
- [x] 4.2 Register `MetadataCorrelationService` dependency injection in the route

## 5. OpenAPI Client Sync

- [x] 5.1 Run `openapi-sync` skill to regenerate `frontend/lib/api/types.gen.ts` and `frontend/lib/api/sdk.gen.ts` after backend endpoint is complete

## 6. Frontend — React Query Hook

- [x] 6.1 Create `frontend/hooks/useMetadataCorrelation.ts` with `useMetadataCorrelation(params)` hook using the generated SDK client; include `enabled: !!(params.x_axis_id && params.y_axis_id)` guard
- [x] 6.2 Add `useAnnotationDefinitions` and `useTaxonomies` calls within the page to populate axis dropdowns (both already exist in `hooks/`)
- [x] 8.1 Create `frontend/app/dashboard/workspace/correlation/page.tsx` with `"use client"` directive
- [x] 8.2 Implement global filter bar: Period selector (Last 30/90/180/365 days, YTD, custom) and Account selector consuming `useWorkspaceFilter`; Base Asset text input as local state
- [x] 8.3 Implement KPI cards row: Win Rate, Max Drawdown, Matched/Total (always), Avg Y-Axis and Max X-Axis (conditionally when axes selected and data loaded)
- [x] 8.4 Implement axis selector section: two grouped `<Select>` dropdowns (X-Axis and Y-Axis) populated from annotation definitions and taxonomies; group labels "Check-in Annotations", "Check-in Taxonomies", "Trade Annotations", "Trade Taxonomies"; show `type` hint in option label
- [x] 8.5 Integrate `CorrelationChartRouter` below axis selectors; show placeholder when no axes selected; show empty state message when `data_points` is empty with explanation text
- [x] 8.6 Implement raw data table below chart: columns Date, Symbol (deep link), Y-Value (named), X-Value (named), Win/Loss; search input filtering by symbol; sortable by any column via `useState` sort state
- [x] 8.7 Add loading skeletons for KPI cards and chart area while `useMetadataCorrelation` is fetching
- [x] 10.3 Add `aria-label` to all chart wrappers for accessibility
- [x] 10.4 Verify the page is responsive: chart and table scroll horizontally on small viewports
