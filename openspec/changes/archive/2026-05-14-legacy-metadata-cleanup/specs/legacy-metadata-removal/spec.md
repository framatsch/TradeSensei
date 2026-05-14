## ADDED Requirements

### Requirement: Legacy tag endpoints are removed from the API
The system SHALL NOT expose any endpoints under `/api/v1/tags`. All tag CRUD routes SHALL be absent. Requests to these endpoints SHALL return 404.

#### Scenario: GET /api/v1/tags returns 404
- **WHEN** an authenticated request is sent to `GET /api/v1/tags`
- **THEN** the server returns 404 Not Found

#### Scenario: POST /api/v1/tags returns 404
- **WHEN** an authenticated request is sent to `POST /api/v1/tags`
- **THEN** the server returns 404 Not Found

### Requirement: Legacy market phase endpoints are removed from the API
The system SHALL NOT expose any endpoints under `/api/v1/market-phases`. Requests SHALL return 404.

#### Scenario: GET /api/v1/market-phases returns 404
- **WHEN** an authenticated request is sent to `GET /api/v1/market-phases`
- **THEN** the server returns 404 Not Found

### Requirement: Legacy checkin field endpoints are removed from the API
The system SHALL NOT expose any endpoints under `/api/v1/checkin-fields`. Requests SHALL return 404.

#### Scenario: GET /api/v1/checkin-fields returns 404
- **WHEN** an authenticated request is sent to `GET /api/v1/checkin-fields`
- **THEN** the server returns 404 Not Found

### Requirement: Legacy tables are dropped from the database
The system's database SHALL NOT contain the tables `tags`, `trade_tags`, `market_phase_definitions`, `checkin_field_definitions`, or `daily_checkin_values` after the migration runs.

#### Scenario: Migration aborts if legacy tables are non-empty
- **WHEN** the Alembic migration runs and any of the legacy tables contain rows
- **THEN** the migration raises an error and does not proceed

#### Scenario: Migration drops tables when empty
- **WHEN** the Alembic migration runs and all legacy tables are empty
- **THEN** all five tables are removed from the database schema

### Requirement: Analytics attribution uses taxonomies, not legacy tags
The system SHALL compute performance attribution (tag/label breakdown in analytics) using the `trade_taxonomies` junction table and `taxonomies` table, not `trade_tags` and `tags`.

#### Scenario: Attribution response includes taxonomy-based breakdowns
- **WHEN** a GET request is sent to the analytics attribution endpoint
- **THEN** the response groups attribution data by taxonomy name
- **AND** no reference to legacy tag IDs appears in the response

### Requirement: Dead frontend files are deleted
The system's frontend codebase SHALL NOT contain the files `hooks/useTags.ts`, `components/tags/TagList.tsx`, or `components/tags/TagBadge.tsx`. The market-phase and checkin-field hook exports SHALL be absent from `hooks/useCheckinDefinitions.ts`.

#### Scenario: TagList import fails at build time if file exists
- **WHEN** the frontend build runs
- **THEN** no import of `TagList` or `TagBadge` from their original paths succeeds (files do not exist)
