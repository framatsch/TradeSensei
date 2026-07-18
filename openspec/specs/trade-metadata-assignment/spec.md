# trade-metadata-assignment Specification

## Purpose
Define expected behavior for assigning and removing taxonomy and annotation metadata on trades.

## Requirements

### Requirement: Assign taxonomy to trade
The system SHALL allow assigning an existing taxonomy to a trade, subject to scope and archive validation.

#### Scenario: Successful assignment
- **WHEN** a POST request assigns a non-archived taxonomy with `scope = trades` or `scope = both` to a trade
- **THEN** the assignment is created and the system returns 201

#### Scenario: Scope mismatch rejected
- **WHEN** a POST request attempts to assign a taxonomy with `scope = checkins` to a trade
- **THEN** the system returns 422 with a scope violation message

#### Scenario: Archived taxonomy assignment rejected
- **WHEN** a POST request attempts to assign an archived taxonomy to a trade
- **THEN** the system returns 422

#### Scenario: Duplicate assignment rejected
- **WHEN** a POST request assigns a taxonomy that is already assigned to the same trade
- **THEN** the system returns 409 Conflict

#### Scenario: Assignment removed on trade delete
- **WHEN** a trade is deleted
- **THEN** all `trade_taxonomies` rows for that trade are also deleted (CASCADE)

### Requirement: Remove taxonomy from trade
The system SHALL allow removing a taxonomy assignment from a trade.

#### Scenario: Successful removal
- **WHEN** a DELETE request targets a specific trade-taxonomy assignment
- **THEN** the assignment row is removed and the system returns 204

### Requirement: Assign annotation to trade
The system SHALL allow assigning an annotation definition to a trade with a typed value that is mapped to the correct typed column.

#### Scenario: Successful int annotation
- **WHEN** a POST request assigns an annotation of type `int` with `value: 5` to a trade
- **THEN** `value_int = 5` is stored, all other value columns are NULL, and the system returns 201

#### Scenario: Successful float annotation
- **WHEN** a POST request assigns an annotation of type `float` with `value: 2.75` to a trade
- **THEN** `value_float = 2.75` is stored and the system returns 201

#### Scenario: Successful bool annotation
- **WHEN** a POST request assigns an annotation of type `bool` with `value: true` to a trade
- **THEN** `value_bool = true` is stored and the system returns 201

#### Scenario: Successful string_enum annotation
- **WHEN** a POST request assigns an annotation of type `string_enum` with a value that exists in `scale_labels.options`
- **THEN** `value_string` is stored and the system returns 201

#### Scenario: Wrong type value rejected
- **WHEN** a POST request submits a string for an `int`-typed annotation
- **THEN** the system returns 422

#### Scenario: Out-of-range value rejected
- **WHEN** a POST request submits a value outside `scale_labels.min`/`scale_labels.max` for an int/float annotation
- **THEN** the system returns 422

#### Scenario: Invalid enum value rejected
- **WHEN** a POST request submits a value not in `scale_labels.options` for a `string_enum` annotation
- **THEN** the system returns 422

#### Scenario: Scope mismatch rejected
- **WHEN** a POST request assigns an annotation with `scope = checkins` to a trade
- **THEN** the system returns 422

#### Scenario: Assignment removed on trade delete
- **WHEN** a trade is deleted
- **THEN** all `trade_annotations` rows for that trade are also deleted (CASCADE)

### Requirement: Update annotation on trade
The system SHALL allow updating an existing annotation assignment value on a trade.

#### Scenario: Successful update
- **WHEN** a PUT request updates the value of an existing trade annotation
- **THEN** the correct typed column is updated and the system returns 200

### Requirement: Remove annotation from trade
The system SHALL allow removing an annotation assignment from a trade.

#### Scenario: Successful removal
- **WHEN** a DELETE request targets a specific trade annotation assignment
- **THEN** the row is removed and the system returns 204

### Requirement: List trade metadata
The system SHALL return the assigned taxonomies and annotations when retrieving a trade's detail.

#### Scenario: Trade detail includes metadata
- **WHEN** a GET request is sent for a trade detail
- **THEN** the response includes `taxonomies` (with definition details) and `annotations` (with definition and value)
- **THEN** archived definitions are included if the assignment exists
