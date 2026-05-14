## Context

The MCP server (`app/api/mcp.py`) currently handles `initialize` and `ping` but has no registered domain tools. The architecture is a standard JSON-RPC 2.0 over HTTP POST (`/mcp/messages`), with PAT auth already enforced via `get_current_user_from_pat`. Existing services (`trade_service`, `playbook_service`, `taxonomy_service`, `trade_metadata_service`) contain all necessary business logic.

## Goals / Non-Goals

**Goals:**
- Expose four domain tools discoverable via `tools/list`
- Implement tools as thin dispatchers that delegate to existing service layer
- Enforce user-scoping on every data operation
- Support optional `portfolio_id` filter on search and sync tools
- Emit manual audit events for mutating tools (`sync_trade_metadata`, `create_strategy_playbook`)

**Non-Goals:**
- PDF/video ingestion or parsing (the calling AI agent provides pre-analyzed text)
- New DB tables or schema changes
- Streaming tool results over SSE (all responses are synchronous JSON-RPC replies)
- Rate limiting or per-tool quota enforcement
- `fastmcp` or any external MCP library dependency

## Decisions

### D1: No new service file — extend existing services
**Decision**: Tool logic lives directly in `app/api/mcp.py` as private handler functions, not in a new `mcp_tools_service.py`.

**Rationale**: Each tool is a thin wrapper over one existing service call (1-5 lines of mapping). Introducing a new service layer for glue code adds indirection without benefit. If tool logic grows complex in future, it can be extracted then.

**Alternative considered**: A dedicated `mcp_tools_service.py` — rejected because it would add a file that contains no reusable business logic, only parameter translation.

---

### D2: Tool dispatch via a registry dict, not chained if/elif
**Decision**: Register handlers in a `_TOOL_HANDLERS: dict[str, Callable]` mapping at module level. Dispatch by looking up `params["name"]` in the registry.

**Rationale**: Eliminates long if/elif chains. Adding a new tool is one dict entry + one handler function. Tools are also enumerable for `tools/list` without duplicating the list.

---

### D3: `search_trades_advanced` — annotation value filtering via subquery, not materialized view
**Decision**: Filter on annotation values using an `EXISTS` subquery against `trade_annotations` + `annotation_definitions` tables.

**Rationale**: Materialized views add operational complexity (refresh scheduling). The annotation-value filter is expected to be used with a narrow primary filter (date range + user) first, making the subquery acceptable in practice.

**Risk**: Without a primary date/user filter, annotation subqueries can be expensive on large datasets. Mitigation: require `date_from`/`date_to` or `symbol` in requests that include annotation filters (enforced at the Pydantic validation layer).

---

### D4: `sync_trade_metadata` taxonomy semantics — replace-all per trade
**Decision**: For each trade in the bulk request, taxonomy assignments are replaced entirely (delete existing + insert new). Annotation values are upserted (insert or update by `annotation_definition_id`).

**Rationale**: Replace-all is unambiguous for the AI agent — it sends the full desired state. Partial add/remove semantics would require the agent to first read current state, diff it, and send delta instructions — unnecessary complexity for the use case.

**Caveat**: This means an agent must send the complete taxonomy list if it only wants to add one tag. The `get_metadata_schema` tool exists to help agents read the full vocabulary first.

---

### D5: `create_strategy_playbook` maps `rules` to `content_markdown`
**Decision**: The tool accepts a `rules` array of strings; they are joined as a Markdown bulleted list and stored in `content_markdown`. Description maps to `description`. No new columns.

**Rationale**: The existing `Playbook` model stores free-form strategy content in `content_markdown` (Text column). Structured rules from an AI agent fit this field when formatted as Markdown. No schema change needed.

---

### D6: `tools/list` returns MCP-standard tool schema
**Decision**: `tools/list` returns an array of tool descriptors following the MCP tool manifest format: `{ name, description, inputSchema }` where `inputSchema` is a JSON Schema object.

**Rationale**: MCP clients (Gemini, Claude) expect this format for tool auto-discovery. Deviating from the spec would break client compatibility.

## Risks / Trade-offs

- **[Risk]** Annotation-value subquery performance on large datasets → Mitigation: require at least one primary filter (date range or symbol) when annotation filters are present; enforced via Pydantic validator
- **[Risk]** Replace-all taxonomy semantics could wipe tags if agent sends incomplete state → Mitigation: document clearly in tool description; agent should call `get_metadata_schema` first to understand vocabulary
- **[Risk]** `sync_trade_metadata` with 100+ trade IDs in one call → Mitigation: enforce a max batch size of 50 trade IDs per call (HTTP 400 if exceeded)

## Migration Plan

1. Deploy backend changes — additive to existing MCP endpoint, no DB changes
2. No frontend changes required
3. Rollback: revert `mcp.py` changes; PAT auth and SSE transport are unaffected
