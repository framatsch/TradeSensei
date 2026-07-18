## ADDED Requirements

### Requirement: Checkin field definitions can be managed per user
The system SHALL allow authenticated users to list, create, update, and delete their check-in field definitions.

#### Scenario: GET /checkin-fields returns user fields
- **WHEN** an authenticated user GETs `/checkin-fields`
- **THEN** the response is 200 with the user's field definitions

#### Scenario: POST creates a new field definition
- **WHEN** an authenticated user POSTs to `/checkin-fields` with a valid payload
- **THEN** the response is 201 with the created field

#### Scenario: DELETE removes a field definition
- **WHEN** an authenticated user DELETEs `/checkin-fields/{id}`
- **THEN** the response is 204 and the field no longer exists

#### Scenario: Unknown field returns 404 on delete
- **WHEN** an authenticated user attempts to delete a non-existent field
- **THEN** the response is 404

### Requirement: Market phase definitions can be managed per user
The system SHALL allow authenticated users to list, create, update, and delete market phase definitions.

#### Scenario: GET /market-phases returns user phases
- **WHEN** an authenticated user GETs `/market-phases`
- **THEN** the response is 200 with the user's phase definitions

#### Scenario: POST creates a new market phase
- **WHEN** an authenticated user POSTs to `/market-phases` with a valid payload
- **THEN** the response is 201 with the created phase

#### Scenario: Duplicate phase label returns 409
- **WHEN** a user POSTs a phase with a label that already exists for their account
- **THEN** the response is 409

### Requirement: DailyCheckinService validates target index ownership
The system SHALL reject check-ins that reference market index IDs not belonging to the requesting user.

#### Scenario: Unknown target_index_id raises validation error
- **WHEN** `DailyCheckinService.create` is called with a `target_index_ids` list containing an ID not owned by the user
- **THEN** `DailyCheckinValidationError` is raised
