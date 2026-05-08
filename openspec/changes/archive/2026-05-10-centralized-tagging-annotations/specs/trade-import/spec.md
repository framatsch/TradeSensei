## ADDED Requirements

### Requirement: Trade detail includes assigned taxonomies
The system SHALL include the list of assigned taxonomies (with full definition data) in the trade detail response.

#### Scenario: Trade with taxonomies returns them
- **WHEN** a GET request retrieves a trade that has taxonomy assignments
- **THEN** the response contains a `taxonomies` array with each assigned taxonomy's definition data

#### Scenario: Archived taxonomy definition included when assigned
- **WHEN** a trade has an assignment to a taxonomy that was subsequently archived
- **THEN** the `taxonomies` array in the response still includes the archived taxonomy definition

### Requirement: Trade detail includes assigned annotations
The system SHALL include the list of assigned annotations (with definition data and typed value) in the trade detail response.

#### Scenario: Trade with annotations returns them
- **WHEN** a GET request retrieves a trade with annotation assignments
- **THEN** the response contains an `annotations` array with each annotation's definition and resolved `value`

#### Scenario: Annotation value is resolved from typed column
- **WHEN** an int-typed annotation is assigned with `value_int = 5`
- **THEN** the API response presents `value: 5` (not the raw column structure)
