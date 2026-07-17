## ADDED Requirements

### Requirement: Single Markdown Content Field
A playbook SHALL store its long-form content in exactly one column, `description`, typed as unbounded `Text`. The system SHALL NOT expose a separate `content_markdown` field on the playbook model, schemas, or API responses.

#### Scenario: Reading a playbook returns a single content field
- **WHEN** a client fetches a playbook via `GET /api/v1/playbooks/{id}`
- **THEN** the response contains a `description` field with the playbook's Markdown content
- **AND** the response does NOT contain a `content_markdown` field

#### Scenario: Content is not length-capped
- **WHEN** a client creates or updates a playbook with a `description` longer than 2000 characters
- **THEN** the system accepts and persists the full value without a length-validation error

### Requirement: Content Migration Prefers content_markdown
When the legacy `content_markdown` column is consolidated into `description`, the system SHALL overwrite each playbook's `description` with the value of its `content_markdown`, unconditionally, for every row.

#### Scenario: content_markdown overwrites description
- **WHEN** the consolidation migration runs on a playbook that has both `description` and `content_markdown` set
- **THEN** the playbook's surviving `description` equals the former `content_markdown` value

#### Scenario: Empty content_markdown clears description
- **WHEN** the consolidation migration runs on a playbook whose `content_markdown` is NULL or empty
- **THEN** the playbook's surviving `description` becomes NULL or empty (mirroring the former `content_markdown`)

#### Scenario: Legacy column removed
- **WHEN** the consolidation migration completes
- **THEN** the `content_markdown` column no longer exists on the `playbooks` table

### Requirement: Create and Update Use the Consolidated Field
The playbook create and update request schemas SHALL accept `description` as optional Markdown content and SHALL NOT accept a `content_markdown` field.

#### Scenario: Create with description
- **WHEN** a client POSTs a new playbook with a `description` value
- **THEN** the created playbook persists that value as its content
- **AND** a `content_markdown` field in the request body is rejected as an unknown field or ignored per schema policy

#### Scenario: Update clears content
- **WHEN** a client PATCHes a playbook with `description` set to null
- **THEN** the playbook's content is cleared
