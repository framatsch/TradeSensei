## ADDED Requirements

### Requirement: Create taxonomy
The system SHALL allow authenticated users to create a taxonomy definition with a name, scope, hex color, optional description, and optional `icon_identifier`. The `icon_identifier` field stores standardized vector-icon library references (e.g. `lucide:trending-down`, `fa-chart-line`). Native emoji strings MUST NOT be accepted.

#### Scenario: Successful creation without icon
- **WHEN** a POST request is sent with valid `name`, `scope`, `color_hex`, and optional `description`, and no `icon_identifier`
- **THEN** the system returns 201 with the created taxonomy including `id`, `is_archived: false`, `created_at`, `updated_at`, and `icon_identifier: null`

#### Scenario: Successful creation with icon_identifier
- **WHEN** a POST request includes a non-empty `icon_identifier` string such as `"lucide:trending-down"`
- **THEN** the system returns 201 with the taxonomy including the stored `icon_identifier` value

#### Scenario: Duplicate name+scope rejected
- **WHEN** a POST request is sent with a `name` and `scope` combination that already exists
- **THEN** the system returns 409 Conflict

#### Scenario: Invalid color_hex rejected
- **WHEN** a POST request contains a `color_hex` that does not match `^#[0-9A-Fa-f]{6}$`
- **THEN** the system returns 422 Unprocessable Entity

### Requirement: List taxonomies
The system SHALL return a list of all non-archived taxonomies by default, with optional scope filtering.

#### Scenario: Default list excludes archived
- **WHEN** a GET request is sent to the taxonomies list endpoint with no filters
- **THEN** only taxonomies with `is_archived = false` are returned

#### Scenario: Filter by scope
- **WHEN** a GET request includes `?scope=trades`
- **THEN** only taxonomies with `scope = trades` or `scope = both` are returned

### Requirement: Update taxonomy
The system SHALL allow updating the `name`, `color_hex`, `description`, and `icon_identifier` of a taxonomy. Scope changes are restricted.

#### Scenario: Successful update including icon_identifier
- **WHEN** a PUT request is sent with valid `name`, `color_hex`, and an updated `icon_identifier`
- **THEN** the system returns 200 with the updated taxonomy, the new `icon_identifier`, and a refreshed `updated_at`

#### Scenario: Clearing icon_identifier
- **WHEN** a PUT request sets `icon_identifier` to `null`
- **THEN** the system returns 200 and the field is stored as NULL

#### Scenario: Scope narrowing blocked when assignments exist
- **WHEN** a PUT request attempts to change `scope` from `both` to `trades` and checkin assignments exist
- **THEN** the system returns 422 with a message indicating scope narrowing is not permitted

#### Scenario: Scope change allowed when no assignments
- **WHEN** a PUT request changes `scope` and no assignments exist in the excluded table
- **THEN** the system returns 200 with updated taxonomy

### Requirement: Delete taxonomy with smart delete
The system SHALL perform a hard delete when no assignments exist and a soft delete (archive) otherwise.

#### Scenario: Hard delete when unused
- **WHEN** a DELETE request is sent for a taxonomy with zero assignments in `trade_taxonomies` and `checkin_taxonomies`
- **THEN** the taxonomy row is removed from the database and the system returns 204

#### Scenario: Soft delete when assigned
- **WHEN** a DELETE request is sent for a taxonomy that has at least one assignment
- **THEN** the taxonomy's `is_archived` is set to `true` and the system returns 200 with the archived taxonomy

### Requirement: Retrieve taxonomy by ID
The system SHALL return a single taxonomy by ID regardless of `is_archived` status.

#### Scenario: Returns archived taxonomy
- **WHEN** a GET request is sent for a taxonomy that is archived
- **THEN** the system returns 200 with the taxonomy including `is_archived: true`

### Requirement: Cascade Hard-Deletion with Danger Zone
The system SHALL support cascading hard-deletion for taxonomies (tags) with active assignments, secured by text-typing validation inside a frontend Danger Zone.

#### Scenario: Deleting taxonomy with assignments
- **WHEN** user initiates delete on a taxonomy with active assignments, is shown the Danger Zone warning, types the exact tag name, and confirms
- **THEN** system SHALL cascade delete all intermediate trade, check-in, and playbook association rows and permanently hard-delete the taxonomy definition
