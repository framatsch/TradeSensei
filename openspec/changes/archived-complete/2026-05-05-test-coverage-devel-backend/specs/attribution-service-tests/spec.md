## ADDED Requirements

### Requirement: AttributionService returns market-phase correlation
The system SHALL compute market-phase correlation data grouped by DailyCheckin phase entries.

#### Scenario: GET /analytics/correlations/market-phase returns 200
- **WHEN** an authenticated user GETs `/portfolios/{portfolio_id}/analytics/correlations/market-phase`
- **THEN** the response is 200 with `ResponseEnvelope[AttributionResponse]`

#### Scenario: Non-owner gets 403
- **WHEN** an authenticated user requests attribution data for a portfolio they do not own
- **THEN** the response is 403

### Requirement: AttributionService raises Spec5NotDeployedError when phase data unavailable
The system SHALL raise `Spec5NotDeployedError` when the `market_phase_definitions` table is not populated.

#### Scenario: Spec5NotDeployedError bubbles to 503
- **WHEN** the market phase definitions table is empty or the feature flag is off
- **THEN** the service raises `Spec5NotDeployedError` and the endpoint returns 503

### Requirement: AttributionService uses cache for repeated requests
The system SHALL cache the attribution response and return it on subsequent identical requests.

#### Scenario: Cache hit skips repository call
- **WHEN** `AttributionService.get_market_phase_correlation` is called and cache has a valid entry
- **THEN** the attribution repository is NOT queried
