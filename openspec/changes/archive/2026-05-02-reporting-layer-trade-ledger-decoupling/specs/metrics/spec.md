## MODIFIED Requirements

### Requirement: Existing metrics endpoints are deprecated
The endpoints `GET /portfolios/{portfolio_id}/metrics/summary`, `GET /portfolios/{portfolio_id}/metrics/equity-curve`, and `GET /portfolios/{portfolio_id}/metrics/drawdown` SHALL be marked as deprecated. They SHALL continue to function for the duration of the deprecation period.

#### Scenario: Deprecated endpoints return deprecation headers
- **WHEN** a client calls any deprecated `/metrics` endpoint
- **THEN** the response SHALL include `Deprecation: true` and `Sunset: <date 6 months from deployment>` HTTP headers

#### Scenario: Deprecated endpoints remain functional during transition
- **WHEN** the deprecated `/metrics` endpoints are called
- **THEN** they return the same response shape as before — no functional regression is introduced by this change

#### Scenario: Removal timeline
- **WHEN** the next major API version is released
- **THEN** the deprecated `/metrics` endpoints are removed and all callers must have migrated to `/analytics/summary`
