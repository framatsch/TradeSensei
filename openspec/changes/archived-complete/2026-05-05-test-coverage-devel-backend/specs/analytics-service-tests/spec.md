## ADDED Requirements

### Requirement: AnalyticsService returns summary from cache when available
The system SHALL return a cached analytics summary and skip DB queries when a valid cache entry exists.

#### Scenario: Cache hit skips repository call
- **WHEN** `AnalyticsService.get_summary` is called and `CacheService.get` returns a serialised `AnalyticsSummary`
- **THEN** the analytics repository is NOT queried and the cached value is returned

### Requirement: AnalyticsService stores result in cache after DB query
The system SHALL serialise and cache the analytics summary after computing it from the database.

#### Scenario: Cache miss triggers DB query and populates cache
- **WHEN** `AnalyticsService.get_summary` is called and the cache is empty (no-op)
- **THEN** the repository is queried and `CacheService.set` is called with the serialised result

### Requirement: AnalyticsService resolves inline filter_config
The system SHALL compute the analytics summary using the inline `filter_config` from the request when no `saved_view_id` is provided.

#### Scenario: Inline filter_config used when no view_id
- **WHEN** `AnalyticsSummaryRequest` contains a `filter_config` and no `saved_view_id`
- **THEN** the summary is computed from the provided filter

### Requirement: AnalyticsService resolves saved view filter
The system SHALL load the `filter_config` from the saved view when a `saved_view_id` is provided.

#### Scenario: Saved view filter_config is loaded
- **WHEN** `AnalyticsSummaryRequest` contains a `saved_view_id` that exists and belongs to the user
- **THEN** the filter_config from that view is used for computation

#### Scenario: Unknown saved_view_id raises error
- **WHEN** `AnalyticsSummaryRequest` contains a `saved_view_id` that does not exist
- **THEN** `SavedDashboardViewNotFoundError` is raised

### Requirement: Analytics summary endpoint returns 200 with valid payload
The system SHALL return a 200 response containing an `AnalyticsSummary` when the user owns the portfolio.

#### Scenario: POST /portfolios/{id}/analytics/summary returns summary
- **WHEN** an authenticated user POSTs to `/portfolios/{portfolio_id}/analytics/summary` with a valid filter_config
- **THEN** the response status is 200 and the body matches `ResponseEnvelope[AnalyticsSummary]`

#### Scenario: Non-owner gets 403
- **WHEN** an authenticated user POSTs to a portfolio they do not own
- **THEN** the response status is 403
