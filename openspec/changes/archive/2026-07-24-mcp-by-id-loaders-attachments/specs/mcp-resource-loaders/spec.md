## ADDED Requirements

### Requirement: Get Trade By ID
The system SHALL provide an MCP tool `get_trade` that returns a single trade owned by the authenticated user, identified by its UUID, including core fields, `notes`, `user_rating`, `tradingview_link`, `playbook_id`, taxonomy assignments, annotation assignments, an image reference count with filenames (not binary content), and the trade's timestamped quick notes embedded inline.

#### Scenario: Load an owned trade
- **WHEN** the authenticated user calls `get_trade` with a `trade_id` that belongs to them
- **THEN** the tool returns the trade's fields, its taxonomy and annotation assignments, image reference filenames and count, and an embedded `quick_notes` array (each with id, content, emotion, created_at)

#### Scenario: Requesting another user's trade
- **WHEN** the user calls `get_trade` with a `trade_id` that does not belong to them
- **THEN** the tool returns an error indicating the trade was not found

#### Scenario: Unknown trade id
- **WHEN** the user calls `get_trade` with a `trade_id` that does not exist
- **THEN** the tool returns an error indicating the trade was not found

### Requirement: Get Check-in By ID
The system SHALL provide an MCP tool `get_checkin` that returns a single daily check-in owned by the authenticated user, identified by its UUID, including notes, market phase, custom metrics, news links, screenshot reference count (not binary content), and full taxonomy and annotation assignment detail.

#### Scenario: Load an owned check-in
- **WHEN** the authenticated user calls `get_checkin` with a `checkin_id` that belongs to them
- **THEN** the tool returns the check-in's fields together with its taxonomy assignments and annotation assignments (each annotation resolved to its typed value)

#### Scenario: Requesting a non-owned or unknown check-in
- **WHEN** the user calls `get_checkin` with a `checkin_id` that does not belong to them or does not exist
- **THEN** the tool returns an error indicating the check-in was not found

### Requirement: Get Taxonomy By ID
The system SHALL provide an MCP tool `get_taxonomy` that returns a single taxonomy (tag) definition owned by the authenticated user, identified by its UUID, including name, scope, color, description, icon identifier, and archived state.

#### Scenario: Load an owned taxonomy
- **WHEN** the authenticated user calls `get_taxonomy` with a `taxonomy_id` that belongs to them
- **THEN** the tool returns the taxonomy's name, scope, color, description, icon identifier, and archived state

#### Scenario: Requesting a non-owned or unknown taxonomy
- **WHEN** the user calls `get_taxonomy` with a `taxonomy_id` that does not belong to them or does not exist
- **THEN** the tool returns an error indicating the taxonomy was not found

### Requirement: Get Annotation Definition By ID
The system SHALL provide an MCP tool `get_annotation_definition` that returns a single annotation definition owned by the authenticated user, identified by its UUID, including name, type, scope, scale labels, description, icon identifier, and archived state.

#### Scenario: Load an owned annotation definition
- **WHEN** the authenticated user calls `get_annotation_definition` with an `annotation_definition_id` that belongs to them
- **THEN** the tool returns the definition's name, type, scope, scale labels, description, icon identifier, and archived state

#### Scenario: Requesting a non-owned or unknown annotation definition
- **WHEN** the user calls `get_annotation_definition` with an `annotation_definition_id` that does not belong to them or does not exist
- **THEN** the tool returns an error indicating the annotation definition was not found
