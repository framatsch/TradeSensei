# mcp-checkin-tools Specification

## Purpose
Define expected behavior for MCP tools that list check-ins, sync metadata, and search trades with annotation filters.

## Requirements

### Requirement: MCP tool — list_checkins

The system SHALL provide a `list_checkins` MCP tool that allows AI agents to query check-ins using the same filter capabilities available in the UI.

#### Scenario: Agent discovers metadata schema then filters check-ins
- **WHEN** an agent calls `get_metadata_schema` and receives taxonomy and annotation_definition IDs
- **AND** then calls `list_checkins` with `annotation_filters` referencing those IDs
- **THEN** the system returns paginated check-ins matching the filter including their taxonomy and annotation assignments

#### Scenario: Agent filters check-ins by taxonomy tag
- **WHEN** `list_checkins` is called with `taxonomy_ids: [<id>]`
- **THEN** only check-ins with that tag assigned are returned

#### Scenario: Agent filters check-ins by annotation value
- **WHEN** `list_checkins` is called with `annotation_filters: [{ annotation_definition_id, operator, value }]`
- **THEN** only check-ins matching the annotation condition are returned

#### Scenario: list_checkins response includes assignments
- **GIVEN** a check-in has taxonomy tags and annotation values set
- **WHEN** `list_checkins` returns that check-in
- **THEN** the response includes `taxonomy_assignments` (list of tag names/ids) and `annotation_assignments` (list of definition name + value)

---

### Requirement: MCP tool — sync_checkin_metadata

The system SHALL provide a `sync_checkin_metadata` MCP tool that allows AI agents to bulk-assign taxonomy tags and annotation values to check-ins.

#### Scenario: Agent assigns annotation values to multiple check-ins
- **WHEN** `sync_checkin_metadata` is called with `checkin_ids` and `annotations`
- **THEN** the system assigns or updates each annotation value for each check-in (upsert semantics)

#### Scenario: Agent assigns taxonomy tags to check-ins
- **WHEN** `sync_checkin_metadata` is called with `checkin_ids` and `taxonomy_ids`
- **THEN** the system assigns each tag to each check-in (skips already-assigned, no error)

---

### Requirement: MCP tool — search_trades_advanced with annotation_filters

The system SHALL extend the existing `search_trades_advanced` MCP tool to support `annotation_filters` in addition to `taxonomy_ids`.

#### Scenario: Agent filters trades by annotation value
- **WHEN** `search_trades_advanced` is called with `annotation_filters`
- **THEN** only trades with matching annotation values are returned

#### Scenario: Agent correlates check-in state with trade results
- **WHEN** an agent calls `list_checkins` to find days where "Market Regime" = "Bear"
- **AND** then calls `search_trades_advanced` with `date_from`/`date_to` covering those days
- **THEN** the agent can compute win rate, P&L, etc. for trades taken on Bear-regime days
