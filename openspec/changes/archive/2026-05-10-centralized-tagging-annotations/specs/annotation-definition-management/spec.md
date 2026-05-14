## ADDED Requirements

### Requirement: Create annotation definition
The system SHALL allow authenticated users to create an annotation definition with a name, type (int, float, bool, string_enum), scope, optional description, optional `scale_labels` JSON, and optional `icon_identifier`. The `icon_identifier` stores standardized vector-icon library references (e.g. `lucide:brain`, `fa-heartbeat`). Native emoji strings MUST NOT be accepted.

#### Scenario: Successful creation without icon
- **WHEN** a POST request is sent with valid `name`, `type`, `scope`, and optional `scale_labels`, and no `icon_identifier`
- **THEN** the system returns 201 with the created definition including `id`, `is_archived: false`, `created_at`, `updated_at`, and `icon_identifier: null`

#### Scenario: Successful creation with icon_identifier
- **WHEN** a POST request includes a non-empty `icon_identifier` such as `"lucide:brain"`
- **THEN** the system returns 201 with the definition including the stored `icon_identifier`

#### Scenario: Duplicate name+scope rejected
- **WHEN** a POST request is sent with a `name` and `scope` combination that already exists
- **THEN** the system returns 409 Conflict

#### Scenario: Invalid type rejected
- **WHEN** a POST request contains a `type` not in `{int, float, bool, string_enum}`
- **THEN** the system returns 422 Unprocessable Entity

### Requirement: List annotation definitions
The system SHALL return a list of all non-archived annotation definitions by default, with optional scope filtering.

#### Scenario: Default list excludes archived
- **WHEN** a GET request is sent to the annotation definitions list endpoint
- **THEN** only definitions with `is_archived = false` are returned

#### Scenario: Filter by scope
- **WHEN** a GET request includes `?scope=checkins`
- **THEN** only definitions with `scope = checkins` or `scope = both` are returned

### Requirement: Update annotation definition
The system SHALL allow updating the `name`, `description`, `scale_labels`, and `icon_identifier` of an annotation definition. Type and scope changes are restricted.

#### Scenario: Name and description update succeeds
- **WHEN** a PUT request updates only `name` and `description`
- **THEN** the system returns 200 with the updated definition

#### Scenario: icon_identifier update succeeds
- **WHEN** a PUT request sets or clears `icon_identifier`
- **THEN** the system returns 200 with the updated definition including the new `icon_identifier` value

### Requirement: Delete annotation definition with smart delete
The system SHALL perform a hard delete when no assignments exist and a soft delete (archive) otherwise.

#### Scenario: Hard delete when unused
- **WHEN** a DELETE request is sent for a definition with zero assignments in both annotation tables
- **THEN** the definition row is removed and the system returns 204

#### Scenario: Soft delete when assigned
- **WHEN** a DELETE request is sent for a definition that has at least one assignment
- **THEN** `is_archived` is set to `true` and the system returns 200

### Requirement: Retrieve annotation definition by ID
The system SHALL return a single annotation definition by ID regardless of `is_archived` status.

#### Scenario: Returns archived definition
- **WHEN** a GET request is sent for an archived annotation definition
- **THEN** the system returns 200 with `is_archived: true`
