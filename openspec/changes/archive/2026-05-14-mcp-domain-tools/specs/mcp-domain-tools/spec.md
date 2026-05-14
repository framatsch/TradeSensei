## ADDED Requirements

### Requirement: Tool Discovery via tools/list
The system SHALL respond to the `tools/list` JSON-RPC method with the complete list of available MCP domain tools including their names, descriptions, and input schemas.

#### Scenario: Successful tool listing
- **WHEN** an authenticated MCP client sends `{ "jsonrpc": "2.0", "id": 1, "method": "tools/list" }`
- **THEN** the server responds with `{ "jsonrpc": "2.0", "id": 1, "result": { "tools": [...] } }` containing descriptors for all four domain tools

#### Scenario: Tool descriptor includes inputSchema
- **WHEN** a client receives the tools/list response
- **THEN** each tool descriptor SHALL contain `name`, `description`, and `inputSchema` (JSON Schema object) fields

---

### Requirement: get_metadata_schema Tool
The system SHALL expose a `get_metadata_schema` MCP tool that returns all active Taxonomies and AnnotationDefinitions for the authenticated user.

#### Scenario: Returns all active taxonomies and annotation definitions
- **WHEN** an authenticated MCP client calls `tools/call` with `{ "name": "get_metadata_schema", "arguments": {} }`
- **THEN** the server returns all non-archived Taxonomies (id, name, scope, color_hex, description) and AnnotationDefinitions (id, name, type, scope, scale_labels, description) belonging to the user

#### Scenario: Archived items excluded
- **WHEN** the user has archived taxonomies or annotation definitions
- **THEN** `get_metadata_schema` MUST NOT include them in the response

#### Scenario: Empty schema
- **WHEN** the user has no active taxonomies or annotation definitions
- **THEN** the tool returns `{ "taxonomies": [], "annotation_definitions": [] }`

---

### Requirement: search_trades_advanced Tool
The system SHALL expose a `search_trades_advanced` MCP tool that returns trades matching multi-dimensional filter criteria scoped to the authenticated user.

#### Scenario: Filter by date range
- **WHEN** a client calls `search_trades_advanced` with `date_from` and `date_to` arguments
- **THEN** only trades with `opened_at` within that range (inclusive) are returned

#### Scenario: Filter by symbol
- **WHEN** a client calls `search_trades_advanced` with a `symbol` argument
- **THEN** only trades matching that symbol (case-insensitive) are returned

#### Scenario: Filter by asset class
- **WHEN** a client calls `search_trades_advanced` with an `asset_class` argument
- **THEN** only trades matching that asset class enum value are returned

#### Scenario: Filter by P&L range
- **WHEN** a client calls `search_trades_advanced` with `pnl_min` and/or `pnl_max` arguments
- **THEN** only trades with `pnl` within the specified range are returned

#### Scenario: Filter by taxonomy tags
- **WHEN** a client calls `search_trades_advanced` with a `taxonomy_ids` array argument
- **THEN** only trades assigned to ALL specified taxonomy IDs are returned (AND semantics)

#### Scenario: Filter by annotation value
- **WHEN** a client calls `search_trades_advanced` with `annotation_filters` (array of `{ annotation_definition_id, operator, value }`)
- **THEN** only trades where the annotation values satisfy all filter conditions are returned

#### Scenario: Optional portfolio scope
- **WHEN** a client calls `search_trades_advanced` with a `portfolio_id` argument
- **THEN** only trades belonging to accounts within that portfolio are returned

#### Scenario: Annotation filter requires primary filter
- **WHEN** a client calls `search_trades_advanced` with `annotation_filters` but without a date range or symbol
- **THEN** the server returns a JSON-RPC error with code -32602 (Invalid params) and message explaining the requirement

#### Scenario: Paginated results
- **WHEN** a client calls `search_trades_advanced`
- **THEN** the response includes `trades`, `total`, `limit`, and `offset` fields; default limit is 50, maximum is 200

#### Scenario: User isolation
- **WHEN** a client calls `search_trades_advanced` with a trade ID or filter that would match another user's trade
- **THEN** only the authenticated user's trades are returned; no cross-user data leaks

---

### Requirement: sync_trade_metadata Tool
The system SHALL expose a `sync_trade_metadata` MCP tool that bulk-updates notes, taxonomy assignments, and annotation values for an array of trade IDs in a single operation.

#### Scenario: Bulk update notes
- **WHEN** a client calls `sync_trade_metadata` with `trade_ids` and a `notes` string
- **THEN** all specified trades have their `notes` field updated to the provided value

#### Scenario: Replace taxonomy assignments
- **WHEN** a client calls `sync_trade_metadata` with `trade_ids` and a `taxonomy_ids` array
- **THEN** each trade's taxonomy assignments are replaced entirely with the provided taxonomy IDs (existing assignments removed, new ones created)

#### Scenario: Upsert annotation values
- **WHEN** a client calls `sync_trade_metadata` with `trade_ids` and an `annotations` array of `{ annotation_definition_id, value }`
- **THEN** each trade's annotation values are upserted (created if not present, updated if existing) for the specified annotation definitions

#### Scenario: Max batch size enforced
- **WHEN** a client calls `sync_trade_metadata` with more than 50 trade IDs
- **THEN** the server returns a JSON-RPC error with code -32602 (Invalid params) and message "Maximum 50 trade IDs per call"

#### Scenario: User isolation on bulk update
- **WHEN** a client provides trade IDs that include trades belonging to other users
- **THEN** only trades owned by the authenticated user are updated; non-owned trade IDs are silently ignored

#### Scenario: Result summary returned
- **WHEN** `sync_trade_metadata` completes successfully
- **THEN** the response includes `{ "updated_count": N }` where N is the number of trades actually updated

#### Scenario: Audit event emitted
- **WHEN** `sync_trade_metadata` completes a bulk update
- **THEN** a manual audit event `trade.bulk_metadata_synced` is emitted with `{ user_id, trade_count }` metadata (no P&L or tag names)

---

### Requirement: create_strategy_playbook Tool
The system SHALL expose a `create_strategy_playbook` MCP tool that persists a fully structured Playbook record from pre-analyzed external content.

#### Scenario: Create playbook with all fields
- **WHEN** a client calls `create_strategy_playbook` with `name`, `description`, `rules` (string array), and optional `target_winrate`
- **THEN** a new Playbook is created with `content_markdown` set to the rules formatted as a Markdown bullet list

#### Scenario: Name uniqueness enforced
- **WHEN** a client calls `create_strategy_playbook` with a name that already exists for the user
- **THEN** the server returns a JSON-RPC error with code -32602 (Invalid params) and message "A playbook with that name already exists"

#### Scenario: Playbook created as active
- **WHEN** `create_strategy_playbook` successfully creates a playbook
- **THEN** the new playbook has `is_active = true`

#### Scenario: Response includes created playbook ID
- **WHEN** `create_strategy_playbook` succeeds
- **THEN** the response includes `{ "playbook_id": "<uuid>", "name": "<name>" }`

#### Scenario: Audit event emitted
- **WHEN** `create_strategy_playbook` successfully creates a playbook
- **THEN** a manual audit event `playbook.created` is emitted with `{ user_id, playbook_id }` metadata (no playbook name)
