## ADDED Requirements

### Requirement: Create a saved dashboard view
A user SHALL be able to create a named dashboard view bound to a specific portfolio, with a validated `filter_config` payload.

#### Scenario: Successful creation
- **WHEN** an authenticated user sends `POST /api/v1/portfolios/{portfolio_id}/views` with a valid name and `filter_config`
- **THEN** the system stores the view and returns HTTP 201 with the created `SavedDashboardView` object including its generated `id`

#### Scenario: filter_config missing required currency_mode
- **WHEN** a user submits a `filter_config` without the `currency_mode` field
- **THEN** the system SHALL default to `currency_mode = "NATIVE"` and persist accordingly

#### Scenario: filter_config with NORMALIZED mode but missing normalize_to
- **WHEN** a user submits `currency_mode = "NORMALIZED"` without providing `normalize_to`
- **THEN** the system SHALL return HTTP 422 with a field-level error indicating `normalize_to` is required when `currency_mode = NORMALIZED`

#### Scenario: filter_config with invalid date range
- **WHEN** `date_from` is later than `date_to` in the filter_config
- **THEN** the system SHALL return HTTP 422 with a descriptive error

#### Scenario: portfolio_id does not belong to user
- **WHEN** the `portfolio_id` in the URL belongs to a different user
- **THEN** the system SHALL return HTTP 404

### Requirement: List saved dashboard views for a portfolio
A user SHALL be able to retrieve all saved views belonging to their portfolio.

#### Scenario: Portfolio has views
- **WHEN** an authenticated user calls `GET /api/v1/portfolios/{portfolio_id}/views`
- **THEN** the system returns HTTP 200 with a list of all `SavedDashboardView` objects for that portfolio, ordered by `updated_at` descending

#### Scenario: Portfolio has no views
- **WHEN** the portfolio exists but has no saved views
- **THEN** the system returns HTTP 200 with an empty list

### Requirement: Update a saved dashboard view
A user SHALL be able to rename a view or update its `filter_config`.

#### Scenario: Successful update
- **WHEN** a user sends `PATCH /api/v1/portfolios/{portfolio_id}/views/{view_id}` with valid fields
- **THEN** the system updates the view, sets `updated_at` to now, and returns HTTP 200 with the updated object

#### Scenario: View belongs to different portfolio
- **WHEN** the `view_id` does not belong to `portfolio_id` in the URL
- **THEN** the system SHALL return HTTP 404

### Requirement: Delete a saved dashboard view
A user SHALL be able to delete a saved dashboard view.

#### Scenario: Successful deletion
- **WHEN** a user sends `DELETE /api/v1/portfolios/{portfolio_id}/views/{view_id}`
- **THEN** the system deletes the view and returns HTTP 204
