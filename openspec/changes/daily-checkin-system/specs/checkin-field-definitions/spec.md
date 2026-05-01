## ADDED Requirements

### Requirement: Create a field definition
The system SHALL allow an authenticated user to create a `CheckinFieldDefinition` via POST `/api/v1/checkin-fields`. The record SHALL require `field_name` (string, max 100 chars, unique per user, lowercase kebab-case) and `field_type` (enum: `integer`, `boolean`). `is_active` SHALL default to `true`. A user SHALL NOT be able to create two active definitions with the same `field_name`.

#### Scenario: Successful creation
- **WHEN** an authenticated user sends POST `/api/v1/checkin-fields` with `field_name="energy"` and `field_type="integer"`
- **THEN** the system SHALL persist the definition and return HTTP 201

#### Scenario: Duplicate field_name rejected
- **WHEN** an authenticated user sends POST `/api/v1/checkin-fields` with a `field_name` that already exists for that user
- **THEN** the system SHALL return HTTP 409 Conflict

#### Scenario: Invalid field_type rejected
- **WHEN** an authenticated user sends POST `/api/v1/checkin-fields` with `field_type="float"`
- **THEN** the system SHALL return HTTP 422 Unprocessable Entity

### Requirement: List field definitions
The system SHALL allow an authenticated user to list their `CheckinFieldDefinition` records via GET `/api/v1/checkin-fields`. An optional `is_active` query parameter SHALL filter results. Only the requesting user's records SHALL be returned.

#### Scenario: List all definitions
- **WHEN** an authenticated user sends GET `/api/v1/checkin-fields`
- **THEN** the system SHALL return HTTP 200 with all definitions for that user

#### Scenario: Filter by active status
- **WHEN** an authenticated user sends GET `/api/v1/checkin-fields?is_active=true`
- **THEN** the system SHALL return only definitions with `is_active=true`

### Requirement: Update a field definition
The system SHALL allow an authenticated user to update `is_active` of an existing definition via PATCH `/api/v1/checkin-fields/{id}`. The `field_name` and `field_type` fields SHALL be immutable after creation — `field_name` references stored JSONB keys in `DailyCheckin.custom_metrics` and changing it would orphan historical data. `field_type` immutability preserves historical metric type contracts. The PATCH endpoint SHALL reject any attempt to modify `field_name` or `field_type` with HTTP 422.

#### Scenario: Deactivate a field
- **WHEN** an authenticated user sends PATCH `/api/v1/checkin-fields/{id}` with `{"is_active": false}`
- **THEN** the system SHALL update the field and return HTTP 200

#### Scenario: field_type change rejected
- **WHEN** an authenticated user sends PATCH `/api/v1/checkin-fields/{id}` with `{"field_type": "boolean"}`
- **THEN** the system SHALL return HTTP 422 Unprocessable Entity indicating `field_type` is immutable

#### Scenario: Cross-user update rejected
- **WHEN** a user sends PATCH `/api/v1/checkin-fields/{id}` where the definition belongs to another user
- **THEN** the system SHALL return HTTP 404

## Design Note: No DELETE endpoint (by design)

Field definitions cannot be deleted — only deactivated. This is intentional: existing `DailyCheckin.custom_metrics` JSONB blobs reference field names by string key. Deleting a definition would orphan historical data with no schema to interpret it. Deactivation preserves the audit trail while blocking the field from new check-ins. To "reuse" a field name, the user reactivates the existing definition. See `design.md` D10.
