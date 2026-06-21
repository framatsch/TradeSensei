## ADDED Requirements

### Requirement: MCP tool — create_taxonomy
The system SHALL provide a `create_taxonomy` MCP tool that creates a new taxonomy definition for the authenticated user.

#### Scenario: Successful taxonomy creation
- **WHEN** `create_taxonomy` is called with valid `name`, `scope`, `color_hex`, and optional `description` and `icon_identifier`
- **THEN** the system creates the taxonomy and returns `{ "taxonomy_id": "<uuid>", "name": "<name>" }`

#### Scenario: Duplicate name+scope rejected
- **WHEN** `create_taxonomy` is called with a `name` and `scope` combination that already exists for the user
- **THEN** the tool returns an error: "taxonomy with this name and scope already exists"

#### Scenario: Invalid color_hex rejected
- **WHEN** `create_taxonomy` is called with a `color_hex` that does not match `^#[0-9A-Fa-f]{6}$`
- **THEN** the tool returns a validation error

### Requirement: MCP tool — update_taxonomy
The system SHALL provide an `update_taxonomy` MCP tool that updates an existing taxonomy definition.

#### Scenario: Successful taxonomy update
- **WHEN** `update_taxonomy` is called with a valid `taxonomy_id` and any subset of `name`, `color_hex`, `description`, `icon_identifier`, `is_archived`
- **THEN** the system updates the provided fields and returns `{ "taxonomy_id": "<uuid>", "name": "<name>", "is_archived": <bool> }`

#### Scenario: Taxonomy not found
- **WHEN** `update_taxonomy` is called with a `taxonomy_id` that does not belong to the authenticated user
- **THEN** the tool returns an error: "taxonomy not found"

#### Scenario: Archive via update
- **WHEN** `update_taxonomy` is called with `is_archived: true`
- **THEN** the taxonomy is archived and no longer returned by `get_metadata_schema`

### Requirement: MCP tool — delete_taxonomy
The system SHALL provide a `delete_taxonomy` MCP tool that archives a taxonomy definition. Hard-delete is not available via MCP — it remains UI-exclusive.

#### Scenario: Delete archives the taxonomy
- **WHEN** `delete_taxonomy` is called with a valid `taxonomy_id`
- **THEN** the taxonomy is archived, removed from `get_metadata_schema` output, and the tool returns `{ "archived": true }`

#### Scenario: Delete blocked by active assignments
- **WHEN** `delete_taxonomy` is called on a taxonomy that still has active trade, check-in, or playbook assignments
- **THEN** the tool returns an error: "has active assignments — remove assignments before deleting"
