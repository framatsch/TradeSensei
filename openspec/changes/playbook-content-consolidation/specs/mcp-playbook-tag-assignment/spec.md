## ADDED Requirements

### Requirement: MCP Tool to Set a Playbook's Taxonomies (Additive)
The MCP server SHALL expose a mutating tool that sets taxonomy tags on a playbook owned by the authenticated PAT user by accepting a list of `taxonomy_ids`. The operation SHALL be additive and idempotent: it inserts any not-yet-linked taxonomies and leaves existing links untouched (upsert with conflict-ignore). It SHALL NOT remove taxonomies that are already assigned but absent from the supplied list. This mirrors the existing `sync_trade_metadata` / `sync_checkin_metadata` convention.

#### Scenario: Assign a set of taxonomies
- **WHEN** an MCP client calls the tool with an owned `playbook_id` and a list of valid `taxonomy_ids` whose scope includes `playbook`
- **THEN** every supplied taxonomy is linked to the playbook
- **AND** the tool returns a success result identifying the playbook and the number of taxonomies now applied

#### Scenario: Idempotent re-application
- **WHEN** the tool is called with a `taxonomy_id` that is already assigned to the playbook
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
The MCP `update_strategy_playbook` tool SHALL accept an optional `taxonomy_ids` list so that a client can set a playbook's content and its tags in a single call. When `taxonomy_ids` is supplied, the same additive, scope-enforced, archived-rejecting behavior as the dedicated set tool SHALL apply. When `taxonomy_ids` is omitted, the playbook's taxonomy assignments SHALL be left unchanged.

#### Scenario: Update content and tags together
- **WHEN** an MCP client calls `update_strategy_playbook` with a new `description` and a `taxonomy_ids` list
- **THEN** the content is updated and the supplied taxonomies are additively assigned in the same call

#### Scenario: Omitting taxonomy_ids leaves tags untouched
- **WHEN** `update_strategy_playbook` is called without `taxonomy_ids`
- **THEN** the playbook's existing taxonomy assignments are unchanged

#### Scenario: Invalid taxonomy during update
- **WHEN** `update_strategy_playbook` is called with a `taxonomy_ids` entry that is invalid, archived, or not playbook-scoped
- **THEN** the tool returns an error and neither the content update nor any assignment is persisted

### Requirement: MCP Tool to List a Playbook's Taxonomies
The MCP server SHALL expose a read tool that returns the taxonomies currently assigned to a playbook owned by the authenticated PAT user.

#### Scenario: List assigned taxonomies
- **WHEN** an MCP client calls the list tool with a valid owned `playbook_id`
- **THEN** the tool returns the set of taxonomies assigned to that playbook

#### Scenario: List for missing playbook
- **WHEN** the `playbook_id` does not belong to the PAT user
- **THEN** the tool returns a not-found error

### Requirement: Audit Logging for MCP Playbook Tag Operations
Mutating MCP playbook tag operations (the dedicated set tool and the `taxonomy_ids` path of `update_strategy_playbook`) SHALL emit an audit event with safe identifiers only (user id, playbook id, taxonomy count/ids) and SHALL NOT include tag names, playbook content, or other sensitive values.

#### Scenario: Setting tags emits a safe audit event
- **WHEN** an MCP set-tags or update-with-tags call completes successfully
- **THEN** an audit event using the `<resource>.<verb>` naming convention is recorded
- **AND** the event metadata contains only safe identifiers (no tag name, no playbook content)
