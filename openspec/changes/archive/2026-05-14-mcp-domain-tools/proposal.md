## Why

The current MCP server provides transport infrastructure (SSE + JSON-RPC) but exposes no domain tools — external AI agents can connect but cannot do anything meaningful with TradeSensei data. This change unlocks the core use cases: AI-assisted performance discovery, bulk trade enrichment, and AI-authored strategy playbooks.

## What Changes

- Add `tools/list` JSON-RPC method so MCP clients can discover available tools
- Add `get_metadata_schema` tool: returns the authenticated user's active Taxonomies and AnnotationDefinitions (their "tagging vocabulary")
- Add `search_trades_advanced` tool: multi-dimensional trade filtering by date range, asset class, symbol, P&L, taxonomy tags, annotation values, and optional portfolio scope
- Add `sync_trade_metadata` tool: bulk-update notes, taxonomy assignments, and annotation values across an array of trade IDs in a single call
- Add `create_strategy_playbook` tool: persist a fully structured Playbook (name, description, rules as `content_markdown`, target win rate) from pre-analyzed external content (AI has already parsed PDF/video)
- **BREAKING** (MCP only): `capabilities.tools` in the `initialize` response changes from `{}` to a populated tool manifest

## Capabilities

### New Capabilities
- `mcp-domain-tools`: Four domain tools exposed via MCP JSON-RPC (`get_metadata_schema`, `search_trades_advanced`, `sync_trade_metadata`, `create_strategy_playbook`) with tool discovery via `tools/list`

### Modified Capabilities
- `mcp-integration`: `initialize` now returns a non-empty `capabilities.tools` manifest; new `tools/list` method added

## Impact

- **Backend — `app/api/mcp.py`**: Extend JSON-RPC dispatch with `tools/list` and four tool handlers
- **Backend — new `app/services/mcp_tools_service.py`**: Business logic for all four tools; delegates to existing `trade_service`, `playbook_service`, `taxonomy_service`, `trade_metadata_service`
- **No DB migrations**: All four tools operate on existing schema; no new tables required
- **No frontend changes**: MCP is a machine-to-machine interface
- **No new packages**: Pure JSON-RPC dispatch; no `fastmcp` library dependency introduced
- **Audit logging**: `sync_trade_metadata` and `create_strategy_playbook` require manual audit events (bulk action + resource creation)
