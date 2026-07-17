## ADDED Requirements

### Requirement: sync_playbook_metadata Tool (Additive Tag Set)
The MCP server SHALL expose a mutating tool named `sync_playbook_metadata` that additively assigns taxonomy tags to a playbook owned by the authenticated PAT user. Its shape and behavior SHALL mirror `sync_trade_metadata` / `sync_checkin_metadata`: it accepts a `playbook_id` and a `taxonomy_ids` list, upserts each link with conflict-ignore, and returns an `updated_count`-style result. The operation SHALL be additive and idempotent and SHALL NOT remove taxonomies already assigned but absent from the supplied list.

Before any insert, the tool SHALL validate the entire `taxonomy_ids` list: each taxonomy MUST be owned by the user, MUST NOT be archived, and MUST have a scope that includes `playbook` (`scope_contains(scope, "playbook")`, matching the REST playbook-taxonomy service). If any id fails validation, the call SHALL fail atomically with no assignments created.

#### Scenario: Assign a set of taxonomies
- **WHEN** an MCP client calls `sync_playbook_metadata` with an owned `playbook_id` and a list of valid, playbook-scoped `taxonomy_ids`
- **THEN** every supplied taxonomy is linked to the playbook
- **AND** the tool returns a success result with an updated count

#### Scenario: Idempotent re-application
- **WHEN** the tool is called with a `taxonomy_id` already assigned to the playbook
- **THEN** no duplicate link is created and the call still succeeds

#### Scenario: Additive, non-destructive
- **WHEN** the playbook already has taxonomy A assigned and the tool is called with only taxonomy B
- **THEN** both A and B are assigned afterwards (A is not removed)

#### Scenario: Taxonomy scope incompatible with playbooks
- **WHEN** any supplied taxonomy's scope does not include `playbook`
- **THEN** the tool returns an error indicating the scope is incompatible with playbooks
- **AND** no assignment is created for any taxonomy in the call

#### Scenario: Invalid or archived taxonomy
- **WHEN** any supplied `taxonomy_id` does not belong to the user or is archived
- **THEN** the tool returns an error and creates no assignments

#### Scenario: Playbook not owned by caller
- **WHEN** the `playbook_id` does not belong to the PAT user (or does not exist)
- **THEN** the tool returns a not-found error and creates no assignments

### Requirement: update_strategy_playbook Accepts Taxonomies
The MCP `update_strategy_playbook` tool SHALL accept an optional `taxonomy_ids` list so a client can set a playbook's content and its tags in a single call, using the same additive, scope-enforced, archived-rejecting logic as `sync_playbook_metadata`. When `taxonomy_ids` is omitted, the playbook's taxonomy assignments SHALL be left unchanged.

#### Scenario: Update content and tags together
- **WHEN** an MCP client calls `update_strategy_playbook` with a new `description` and a `taxonomy_ids` list
- **THEN** the content is updated and the supplied taxonomies are additively assigned in the same call

#### Scenario: Omitting taxonomy_ids leaves tags untouched
- **WHEN** `update_strategy_playbook` is called without `taxonomy_ids`
- **THEN** the playbook's existing taxonomy assignments are unchanged

#### Scenario: Invalid taxonomy during update
- **WHEN** `update_strategy_playbook` is called with a `taxonomy_ids` entry that is invalid, archived, or not playbook-scoped
- **THEN** the tool returns an error and neither the content update nor any assignment is persisted

### Requirement: Playbook Read Tools Return Assigned Taxonomies
Consistent with how `list_checkins` returns taxonomy assignments per check-in, the MCP `get_strategy_playbook` and `list_strategy_playbooks` tools SHALL include the taxonomies currently assigned to each playbook in their responses. No standalone playbook-taxonomy list tool is provided.

#### Scenario: get returns assigned taxonomies
- **WHEN** an MCP client calls `get_strategy_playbook` for an owned playbook that has taxonomies assigned
- **THEN** the response includes the assigned taxonomies

#### Scenario: list returns assigned taxonomies
- **WHEN** an MCP client calls `list_strategy_playbooks`
- **THEN** each returned playbook includes its assigned taxonomies

### Requirement: Audit Logging for MCP Playbook Tag Operations
Mutating MCP playbook tag operations (`sync_playbook_metadata` and the `taxonomy_ids` path of `update_strategy_playbook`) SHALL emit an audit event with safe identifiers only (user id, playbook id, taxonomy count) and SHALL NOT include tag names, playbook content, or other sensitive values. This mirrors the `*.bulk_metadata_synced` audit events emitted by `sync_trade_metadata` / `sync_checkin_metadata`.

#### Scenario: Setting tags emits a safe audit event
- **WHEN** a `sync_playbook_metadata` or update-with-tags call completes successfully
- **THEN** an audit event using the `<resource>.<verb>` naming convention is recorded
- **AND** the event metadata contains only safe identifiers (no tag name, no playbook content)
