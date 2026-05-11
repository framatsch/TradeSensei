## ADDED Requirements

### Requirement: Metadata correlation endpoint joins checkins and trades by date

The system SHALL expose `GET /api/v1/analytics/metadata-correlation` with the following query parameters:
- `portfolio_id: UUID` (required)
- `x_axis_type: Literal["checkin_annotation", "checkin_taxonomy", "trade_annotation", "trade_taxonomy"]` (required)
- `x_axis_id: UUID` — annotation definition ID or taxonomy ID (required)
- `y_axis_type: Literal["checkin_annotation", "checkin_taxonomy", "trade_annotation", "trade_taxonomy"]` (required)
- `y_axis_id: UUID` — annotation definition ID or taxonomy ID (required)
- `date_from: date` (optional)
- `date_to: date` (optional)
- `account_ids: list[UUID]` (optional, repeatable query param)
- `base_asset: str` (optional, filters by trade symbol prefix)

The endpoint SHALL:
1. Fetch all trades in the portfolio (filtered by account/date/base_asset) where `closed_at IS NOT NULL`.
2. For each trade, derive `trade_date = date(closed_at)` and look up the checkin with `checkin.date = trade_date`.
3. Resolve the X-axis value from the checkin (annotation value or taxonomy membership boolean) and Y-axis value from the trade (or vice-versa depending on axis_type).
4. Return only pairs where both X and Y values are non-null.
5. Include aggregate KPIs computed from the filtered trade set (not only matched pairs): `win_rate`, `max_drawdown_pct`, `matched_count`, `total_trades_count`.

#### Scenario: Returns correlated pairs for continuous × continuous axes
- **GIVEN** a portfolio with 10 closed trades, each with a closing date matching a check-in with a "Sleep Quality" annotation, and each trade having an "R-Multiple" annotation
- **WHEN** the client calls `GET /api/v1/analytics/metadata-correlation?x_axis_type=checkin_annotation&x_axis_id=<sleep_quality_id>&y_axis_type=trade_annotation&y_axis_id=<r_multiple_id>`
- **THEN** the response contains `data_points` with 10 entries, each with `x_value` (numeric), `y_value` (numeric), `trade_id`, `date`
- **AND** `x_axis_data_type: "float"` and `y_axis_data_type: "float"`

#### Scenario: Returns empty data_points when no checkin matches trade dates
- **GIVEN** a portfolio with 5 closed trades on dates with no check-ins
- **WHEN** the client calls the endpoint with any valid axis configuration
- **THEN** `data_points` is an empty array `[]`
- **AND** `kpis.matched_count = 0` and `kpis.total_trades_count = 5`

#### Scenario: Taxonomy axis returns discrete string values
- **GIVEN** trades with taxonomy "FOMO" or "On-Plan" assigned, and check-ins with "Poor Sleep" taxonomy assigned
- **WHEN** axes are both taxonomy types
- **THEN** each data point has `x_label: str` (taxonomy name) and `y_label: str` (taxonomy name)
- **AND** `x_axis_data_type: "taxonomy"` and `y_axis_data_type: "taxonomy"`

#### Scenario: Mixed annotation types return correct data_type markers
- **GIVEN** X is a `string_enum` checkin annotation and Y is a `float` trade annotation
- **THEN** `x_axis_data_type: "string_enum"` and `y_axis_data_type: "float"`

### Requirement: Metadata correlation endpoint returns aggregate KPIs

The response `kpis` object SHALL always contain:
- `win_rate: Decimal` — fraction of winning trades (PnL > 0) in the filtered trade set
- `max_drawdown_pct: Decimal` — maximum drawdown percentage of the filtered trade equity curve
- `matched_count: int` — number of correlated pairs returned
- `total_trades_count: int` — number of trades in the filtered set before correlation join

#### Scenario: KPIs reflect the global filter, not just matched pairs
- **GIVEN** 20 trades matching the filter, 12 of which have linked check-ins
- **WHEN** the endpoint is called
- **THEN** `kpis.total_trades_count = 20` and `kpis.matched_count = 12`
- **AND** `kpis.win_rate` is computed from all 20 trades, not just the 12

### Requirement: Correlation endpoint validates axis configuration

- **IF** `x_axis_type` refers to a `checkin_annotation` but the annotation definition has `scope = "trades"` → return HTTP 422 with descriptive error.
- **IF** `x_axis_id` does not belong to the authenticated user's portfolio → return HTTP 404.
- **IF** `x_axis_id == y_axis_id` and `x_axis_type == y_axis_type` → return HTTP 422 ("X and Y axes must be different").
