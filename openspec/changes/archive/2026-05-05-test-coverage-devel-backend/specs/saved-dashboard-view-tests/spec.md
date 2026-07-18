## ADDED Requirements

### Requirement: Saved dashboard views can be created by a portfolio owner
The system SHALL create a saved view scoped to a portfolio when the requesting user owns it.

#### Scenario: POST creates view and returns 201
- **WHEN** an authenticated owner POSTs to `/portfolios/{id}/views` with a valid name and filter_config
- **THEN** the response is 201 and the body contains the created `SavedDashboardViewRead`

#### Scenario: Non-owner cannot create view
- **WHEN** a non-owner POSTs to `/portfolios/{id}/views`
- **THEN** the response is 403

### Requirement: Saved dashboard views can be listed per portfolio
The system SHALL return all saved views for a portfolio owned by the requesting user.

#### Scenario: GET returns list of views
- **WHEN** an authenticated owner GETs `/portfolios/{id}/views`
- **THEN** the response is 200 with a list of `SavedDashboardViewRead` for that portfolio

### Requirement: Saved dashboard views can be retrieved by ID
The system SHALL return a single view by its ID when it belongs to the requesting user's portfolio.

#### Scenario: GET by ID returns view
- **WHEN** an authenticated owner GETs `/portfolios/{id}/views/{view_id}`
- **THEN** the response is 200 with the matching view

#### Scenario: Unknown view returns 404
- **WHEN** an authenticated user GETs a view ID that does not exist
- **THEN** the response is 404

### Requirement: Saved dashboard views can be updated
The system SHALL allow the owner to rename or update the filter_config of an existing view.

#### Scenario: PATCH updates view
- **WHEN** an authenticated owner PATCHes `/portfolios/{id}/views/{view_id}` with a new name
- **THEN** the response is 200 and the view name is updated

### Requirement: Saved dashboard views can be deleted
The system SHALL delete a saved view when requested by its owner.

#### Scenario: DELETE removes view
- **WHEN** an authenticated owner DELETEs `/portfolios/{id}/views/{view_id}`
- **THEN** the response is 204 and the view no longer exists
