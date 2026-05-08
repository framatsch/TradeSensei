## ADDED Requirements

### Requirement: Assign taxonomy to check-in
The system SHALL allow assigning an existing taxonomy to a check-in, subject to scope and archive validation.

#### Scenario: Successful assignment
- **WHEN** a POST request assigns a non-archived taxonomy with `scope = checkins` or `scope = both` to a check-in
- **THEN** the assignment is created and the system returns 201

#### Scenario: Scope mismatch rejected
- **WHEN** a POST request attempts to assign a taxonomy with `scope = trades` to a check-in
- **THEN** the system returns 422 with a scope violation message

#### Scenario: Duplicate assignment rejected
- **WHEN** a taxonomy is already assigned to the check-in
- **THEN** the system returns 409 Conflict

#### Scenario: Assignment removed on check-in delete
- **WHEN** a check-in is deleted
- **THEN** all `checkin_taxonomies` rows for that check-in are deleted (CASCADE)

### Requirement: Remove taxonomy from check-in
The system SHALL allow removing a taxonomy assignment from a check-in.

#### Scenario: Successful removal
- **WHEN** a DELETE request targets a specific check-in taxonomy assignment
- **THEN** the row is removed and the system returns 204

### Requirement: Assign annotation to check-in
The system SHALL allow assigning an annotation definition to a check-in with a typed value mapped to the correct column.

#### Scenario: Successful annotation
- **WHEN** a POST request assigns a valid annotation to a check-in with a correctly typed value
- **THEN** the correct typed column is populated and the system returns 201

#### Scenario: Scope mismatch rejected
- **WHEN** a POST request assigns an annotation with `scope = trades` to a check-in
- **THEN** the system returns 422

#### Scenario: Invalid value rejected
- **WHEN** a POST request submits an out-of-range or wrong-type value for a check-in annotation
- **THEN** the system returns 422

#### Scenario: Assignment removed on check-in delete
- **WHEN** a check-in is deleted
- **THEN** all `checkin_annotations` rows for that check-in are deleted (CASCADE)

### Requirement: Update annotation on check-in
The system SHALL allow updating an existing annotation assignment value on a check-in.

#### Scenario: Successful update
- **WHEN** a PUT request updates an existing check-in annotation value
- **THEN** the correct typed column is updated and the system returns 200

### Requirement: Remove annotation from check-in
The system SHALL allow removing an annotation assignment from a check-in.

#### Scenario: Successful removal
- **WHEN** a DELETE request targets a check-in annotation assignment
- **THEN** the row is removed and the system returns 204

### Requirement: List check-in metadata
The system SHALL include assigned taxonomies and annotations when retrieving a check-in's detail.

#### Scenario: Check-in detail includes metadata
- **WHEN** a GET request is sent for a check-in detail
- **THEN** the response includes `taxonomies` and `annotations` with their definition details and values
