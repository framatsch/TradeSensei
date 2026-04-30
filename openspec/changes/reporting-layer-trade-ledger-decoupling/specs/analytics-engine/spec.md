## ADDED Requirements

### Requirement: Compute analytics summary from inline filter_config
The analytics engine SHALL accept an inline `filter_config` and return a fully computed `AnalyticsSummary` without returning any raw trade records.

#### Scenario: Successful ad-hoc analytics request
- **WHEN** a user sends `POST /api/v1/portfolios/{portfolio_id}/analytics/summary` with a valid `filter_config`
- **THEN** the system executes all aggregation server-side and returns HTTP 200 with an `AnalyticsSummary` object

#### Scenario: Response includes mandatory currency field
- **WHEN** an `AnalyticsSummary` is returned
- **THEN** every monetary field SHALL be expressed in the currency identified by the `currency` field in the response

#### Scenario: Fewer than 2 matching trades
- **WHEN** the filter produces 0 or 1 matching closed trades
- **THEN** `sharpe_ratio` SHALL be `null` in the response, and all other computable fields SHALL be present (zeroed where appropriate)

#### Scenario: filter_config references non-existent playbook_ids
- **WHEN** playbook UUIDs in `filter_config` do not belong to the portfolio
- **THEN** the system SHALL return HTTP 422 with an error indicating the invalid IDs

### Requirement: Compute analytics summary from a saved view
The analytics engine SHALL accept a `view_id` as an alias for its `filter_config` and return the same response shape as inline mode.

#### Scenario: Successful view-based analytics request
- **WHEN** a user sends `POST /api/v1/portfolios/{portfolio_id}/analytics/summary` with `{"view_id": "<uuid>"}` in the request body (and `filter_config` omitted)
- **THEN** the system loads the view's `filter_config` and computes the summary as if it were submitted inline

#### Scenario: View not found or belongs to different portfolio
- **WHEN** the `view_id` does not exist or belongs to a different portfolio
- **THEN** the system SHALL return HTTP 404

### Requirement: Analytics endpoint serves equity curve and drawdown curve
The analytics summary response SHALL include equity curve and drawdown curve data, bounded at `EQUITY_CURVE_MAX_POINTS`.

#### Scenario: Large trade count
- **WHEN** the filter matches more trades than `EQUITY_CURVE_MAX_POINTS`
- **THEN** the equity curve SHALL be downsampled server-side; raw trade records SHALL NOT be returned to the frontend for client-side downsampling

#### Scenario: No closed trades in range
- **WHEN** the filter produces zero closed trades
- **THEN** `equity_curve` and `drawdown_curve` SHALL both be empty lists

### Requirement: Analytics endpoint does not return raw trade rows
The `/analytics/summary` endpoint MUST NOT include individual trade records or any paginated trade list in its response.

#### Scenario: Attempt to extract raw data from analytics response
- **WHEN** the analytics summary response is inspected
- **THEN** it SHALL contain only computed metric fields and curve arrays — no `trades` array, no cursor token, no raw PnL per trade

### Requirement: Multi-currency NATIVE mode handling
When `currency_mode = NATIVE` and the filtered trades span multiple currencies, the system SHALL not silently aggregate incompatible monetary values. Instead it SHALL return per-currency sub-summaries with a warning, so the user understands the breakdown without being blocked.

#### Scenario: Single-currency portfolio in NATIVE mode
- **WHEN** all filtered trades share the same currency
- **THEN** the response `currency` field is set to that currency, `currencies` contains exactly one entry, and all monetary values are correct

#### Scenario: Multi-currency portfolio in NATIVE mode
- **WHEN** filtered trades span more than one currency and `currency_mode = NATIVE`
- **THEN** the system SHALL return HTTP 200 with:
  - `currency = null` (no single currency applies)
  - `multi_currency_warning: true`
  - `currencies`: a list of per-currency `AnalyticsSummary` sub-objects, each with its own `currency` field and independently computed metrics
  - Top-level monetary aggregate fields (`gross_profit`, `gross_loss`, `avg_win`, `avg_loss`, `expectancy`) set to `null`
  - Non-monetary fields (`win_rate`, `profit_factor`, `total_trades`, `winning_trades`, `losing_trades`, `max_consecutive_wins`, `max_consecutive_losses`) computed across all trades regardless of currency
  - `sharpe_ratio` set to `null` when currencies are mixed (cross-currency Sharpe is meaningless)

#### Scenario: Frontend receives multi-currency warning
- **WHEN** `multi_currency_warning = true` is present in the response
- **THEN** the frontend SHOULD display a notice informing the user that monetary values are broken down by currency and offering to switch to `NORMALIZED` mode

### Requirement: Multi-currency NORMALIZED mode handling
When `currency_mode = NORMALIZED`, the system SHALL convert all trade PnL values to `normalize_to` using the historical ECB FX rate on `trade.closed_at::date`.

#### Scenario: All FX rates available
- **WHEN** all required historical FX rates exist in the `fx_rates` table
- **THEN** the response contains normalized monetary values and `currency = normalize_to`

#### Scenario: FX rate missing for some trade dates
- **WHEN** a historical FX rate is not available within ±3 calendar days of a trade's close date
- **THEN** the affected trades are excluded from aggregation and their IDs are listed in `fx_rate_missing_trade_ids` in the response

#### Scenario: FX rate gap fallback
- **WHEN** the exact close date has no FX rate but a rate within ±3 calendar days exists
- **THEN** the nearest available rate is used and the trade is included normally
