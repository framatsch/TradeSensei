## ADDED Requirements

### Requirement: Market index definitions can be created and listed
The system SHALL allow authenticated users to create market index definitions and retrieve their list.

#### Scenario: POST /market-indexes creates index definition
- **WHEN** an authenticated user POSTs to `/market-indexes` with a valid name and ticker
- **THEN** the response is 201 with the created index definition

#### Scenario: GET /market-indexes returns user indexes
- **WHEN** an authenticated user GETs `/market-indexes`
- **THEN** the response is 200 with a list of their index definitions

### Requirement: Market index definitions can be updated and deleted
The system SHALL allow the owner to modify or remove a market index definition.

#### Scenario: PATCH updates an index definition
- **WHEN** an authenticated owner PATCHes `/market-indexes/{id}`
- **THEN** the response is 200 with the updated definition

#### Scenario: DELETE removes an index definition
- **WHEN** an authenticated owner DELETEs `/market-indexes/{id}`
- **THEN** the response is 204

#### Scenario: Non-owner cannot delete an index
- **WHEN** a different user attempts to DELETE another user's index definition
- **THEN** the response is 404 or 403

### Requirement: MarketIndexDefinitionService enforces user ownership
The system SHALL raise an appropriate error when a user tries to modify an index that does not belong to them.

#### Scenario: Get by ID for wrong user returns None
- **WHEN** `MarketIndexDefinitionRepository.get_by_id` is called with the wrong user_id
- **THEN** it returns `None`
