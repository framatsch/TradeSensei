## ADDED Requirements

### Requirement: MCP tool — create_annotation_definition
The system SHALL provide a `create_annotation_definition` MCP tool that creates a new annotation definition for the authenticated user.

#### Scenario: Successful annotation definition creation
- **WHEN** `create_annotation_definition` is called with valid `name`, `type` (`int`, `float`, `bool`, or `string_enum`), `scope`, and optional `description`, `icon_identifier`, `scale_labels`
- **THEN** the system creates the annotation definition and returns `{ "annotation_definition_id": "<uuid>", "name": "<name>", "type": "<type>" }`

#### Scenario: string_enum type with options
- **WHEN** `create_annotation_definition` is called with `type: "string_enum"` and `scale_labels: { "options": ["Bear", "Bull", "Neutral"] }`
- **THEN** the annotation definition is created with those enum options stored in `scale_labels`

#### Scenario: Duplicate name+scope rejected
- **WHEN** `create_annotation_definition` is called with a `name` and `scope` combination that already exists for the user
- **THEN** the tool returns an error: "annotation definition with this name and scope already exists"

### Requirement: MCP tool — update_annotation_definition
The system SHALL provide an `update_annotation_definition` MCP tool that updates an existing annotation definition.

#### Scenario: Successful annotation definition update
- **WHEN** `update_annotation_definition` is called with a valid `annotation_definition_id` and any subset of `name`, `type`, `scope`, `description`, `icon_identifier`, `scale_labels`, `is_archived`
- **THEN** the system updates the provided fields and returns `{ "annotation_definition_id": "<uuid>", "name": "<name>", "is_archived": <bool> }`

#### Scenario: Annotation definition not found
- **WHEN** `update_annotation_definition` is called with an `annotation_definition_id` that does not belong to the authenticated user
- **THEN** the tool returns an error: "annotation definition not found"

### Requirement: MCP tool — delete_annotation_definition
The system SHALL provide a `delete_annotation_definition` MCP tool that archives an annotation definition. Hard-delete is not available via MCP — it remains UI-exclusive.

#### Scenario: Delete archives the annotation definition
- **WHEN** `delete_annotation_definition` is called with a valid `annotation_definition_id`
- **THEN** the annotation definition is archived, removed from `get_metadata_schema` output, and the tool returns `{ "archived": true }`

#### Scenario: Delete blocked by active assignments
- **WHEN** `delete_annotation_definition` is called on a definition that still has active annotation values on trades or check-ins
- **THEN** the tool returns an error: "has active assignments — remove assignments before deleting"
