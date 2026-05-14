## 1. Tool Registry & Dispatch

- [x] 1.1 Define `_TOOL_REGISTRY: dict[str, dict]` in `app/api/mcp.py` mapping tool names to their handler callables and JSON Schema input descriptors
- [x] 1.2 Add `tools/list` method handler to JSON-RPC dispatch: return `{ "tools": [...] }` from the registry
- [x] 1.3 Add `tools/call` method handler to JSON-RPC dispatch: look up `params["name"]` in registry, call handler, return result or `-32601` error for unknown tool
- [x] 1.4 Update `initialize` response: populate `capabilities.tools` with tool names from the registry instead of empty dict

## 2. get_metadata_schema Tool

- [x] 2.1 Implement `_handle_get_metadata_schema(user_id, db, arguments)` in `app/api/mcp.py`: query non-archived Taxonomies for user via `taxonomy_service` or direct repo call
- [x] 2.2 Add AnnotationDefinition query to same handler: return non-archived definitions via `annotation_definition` repo
- [x] 2.3 Serialize both collections to plain dicts (id, name, scope, color_hex/type/scale_labels, description) and return `{ "taxonomies": [...], "annotation_definitions": [...] }`
- [x] 2.4 Register `get_metadata_schema` in `_TOOL_REGISTRY` with input schema `{ "type": "object", "properties": {} }`

## 3. search_trades_advanced Tool

- [x] 3.1 Define Pydantic model `AdvancedTradeSearchParams` with fields: `date_from`, `date_to`, `symbol`, `asset_class`, `pnl_min`, `pnl_max`, `taxonomy_ids`, `annotation_filters`, `portfolio_id`, `limit` (max 200, default 50), `offset` (default 0)
- [x] 3.2 Add validator: if `annotation_filters` present, require `date_from`/`date_to` or `symbol`; raise `ValueError` if missing
- [x] 3.3 Implement `_handle_search_trades_advanced(user_id, db, arguments)`: parse arguments into `AdvancedTradeSearchParams`, build SQLAlchemy query with `WHERE user_id = :user_id`
- [x] 3.4 Add date range filter (`opened_at BETWEEN date_from AND date_to`) when provided
- [x] 3.5 Add symbol filter (case-insensitive ILIKE) when provided
- [x] 3.6 Add asset_class enum filter when provided
- [x] 3.7 Add P&L range filter (`pnl >= pnl_min AND pnl <= pnl_max`) when provided
- [x] 3.8 Add taxonomy filter via JOIN on `trade_taxonomies` for each taxonomy_id (AND semantics — one JOIN per ID)
- [x] 3.9 Add annotation_filter as `EXISTS` subquery on `trade_annotations` + `annotation_definitions` for each filter entry; support operators: `eq`, `lt`, `gt`, `lte`, `gte`
- [x] 3.10 Add optional portfolio scope filter via JOIN `accounts` WHERE `portfolio_id = :portfolio_id`
- [x] 3.11 Return `{ "trades": [...], "total": N, "limit": L, "offset": O }` with trades serialized as minimal dicts (id, symbol, direction, asset_class, opened_at, closed_at, pnl, net_pnl, playbook_id)
- [x] 3.12 Register `search_trades_advanced` in `_TOOL_REGISTRY` with full JSON Schema input descriptor

## 4. sync_trade_metadata Tool

- [x] 4.1 Define Pydantic model `SyncTradeMetadataParams` with fields: `trade_ids` (list, max 50), `notes` (optional str), `taxonomy_ids` (optional list of UUID), `annotations` (optional list of `{ annotation_definition_id, value }`)
- [x] 4.2 Add validator: reject if `len(trade_ids) > 50`; raise `ValueError`
- [x] 4.3 Implement `_handle_sync_trade_metadata(user_id, db, arguments)`: fetch all trades by IDs scoped to `user_id`, silently ignore non-owned or non-existent IDs
- [x] 4.4 If `notes` provided: bulk update `Trade.notes` for matched trades
- [x] 4.5 If `taxonomy_ids` provided: delete all `TradeTaxonomy` rows for matched trades, insert new rows for each `(trade_id, taxonomy_id)` pair
- [x] 4.6 If `annotations` provided: upsert `TradeAnnotation` rows (`ON CONFLICT (trade_id, annotation_definition_id) DO UPDATE SET value = ...`)
- [x] 4.7 Emit manual audit event `trade.bulk_metadata_synced` with `{ "user_id": user_id, "trade_count": N }` after successful update
- [x] 4.8 Return `{ "updated_count": N }`
- [x] 4.9 Register `sync_trade_metadata` in `_TOOL_REGISTRY` with full JSON Schema input descriptor

## 5. create_strategy_playbook Tool

- [x] 5.1 Define Pydantic model `CreateStrategyPlaybookParams` with fields: `name` (str, max 100), `description` (optional str), `rules` (list[str], min 1 item), `target_winrate` (optional float 0-1)
- [x] 5.2 Implement `_handle_create_strategy_playbook(user_id, db, arguments)`: parse params, check name uniqueness for user (raise -32602 if duplicate), format `rules` list as Markdown bullet list for `content_markdown`
- [x] 5.3 Create `Playbook` ORM instance with `is_active=True`, call `db.flush()` to get generated ID
- [x] 5.4 Emit manual audit event `playbook.created` with `{ "user_id": user_id, "playbook_id": str(playbook.id) }`
- [x] 5.5 Return `{ "playbook_id": str(playbook.id), "name": playbook.name }`
- [x] 5.6 Register `create_strategy_playbook` in `_TOOL_REGISTRY` with full JSON Schema input descriptor

## 6. Error Handling & Integration

- [x] 6.1 Add a `_tool_error(code, message)` helper that returns a standard JSON-RPC error dict
- [x] 6.2 Wrap all tool handlers in try/except: catch `ValueError` from Pydantic validators → return `-32602` error; catch unexpected exceptions → log and return `-32603` (Internal error)
- [x] 6.3 Inject `AsyncSession` (via `Depends`) into the `mcp_messages` endpoint and thread it through to all tool handlers
- [x] 6.4 Wrap mutating tool handlers (`sync_trade_metadata`, `create_strategy_playbook`) in a DB transaction (commit on success, rollback on error)

## 7. Documentation — `docs/mcp-client-integration.md`

- [x] 7.1 Add a **"Available Tools"** section listing all four tools (`get_metadata_schema`, `search_trades_advanced`, `sync_trade_metadata`, `create_strategy_playbook`) with a one-sentence description and their input parameters table (param name, type, required, description)
- [x] 7.2 Add a **"Prompt Examples"** section with at least four realistic AI-agent prompts mapped to the tools they use:
  - Performance discovery: *"Show me all losing trades from last week where my Mood annotation was below 5"* → `search_trades_advanced`
  - Automated enrichment: *"Tag my trades from May 6th 2026 afternoon with 'Macro Volatility'"* → `get_metadata_schema` + `search_trades_advanced` + `sync_trade_metadata`
  - Strategy creation: *"Create a Breakout Momentum playbook from these rules: ..."* → `create_strategy_playbook`
  - Pattern correlation: *"What is my win rate on LONG EQUITY trades in the first hour of the day?"* → `search_trades_advanced`
- [x] 7.3 Add a **"Workflow Example"** showing a multi-step agent session: (1) call `get_metadata_schema` to learn vocabulary, (2) call `search_trades_advanced` to find trades, (3) call `sync_trade_metadata` to enrich them — with annotated JSON-RPC snippets for each step
- [x] 7.4 Add a **"Constraints & Limits"** section documenting: max 50 trade IDs per `sync_trade_metadata` call, max 200 results per `search_trades_advanced` page, annotation filters require a date or symbol primary filter

## 8. In-App Help — `frontend/lib/help-content.ts`

- [x] 8.1 Add a new top-level help section `"AI & MCP Integration"` with an entry **"MCP Integration"** explaining what MCP is in one sentence and why a user would use it (connect AI agents like Claude or Gemini to their TradeSensei data)
- [x] 8.2 Add entry **"Personal Access Token (PAT)"** under the new section: what it is, that it's required for MCP, that it's shown only once, and where to generate one (Settings → API & Tokens)
- [x] 8.3 Add entry **"AI Prompt Examples"** — a short curated list of copy-paste-ready prompts the user can send to their AI agent once connected, matching the four use cases from the docs (performance review, enrichment, strategy creation, pattern analysis)
- [x] 8.4 Regenerate `docs/HELP_GLOSSARY.md` from the updated `help-content.ts` using `npm run export-help` (from `frontend/`) so the static glossary stays in sync

## 9. In-App Contextual Help — `ApiTokensSettings.tsx`

- [x] 9.1 Below the existing "Generate personal access tokens for MCP integrations" subtitle, add a collapsible **"What can I do with MCP?"** info block listing the four tool use cases as bullet points with example prompts
- [x] 9.2 Add a **"Learn more"** link pointing to `docs/mcp-client-integration.md` (or an internal help anchor) so users can navigate to the full guide directly from the settings page

## 10. Tests

- [x] 10.1 Add unit tests in `tests/test_mcp_api.py` for `tools/list`: verify all four tools appear with `name`, `description`, `inputSchema`
- [x] 10.2 Add test for `get_metadata_schema`: archived items excluded, empty response when no active schema
- [x] 10.3 Add tests for `search_trades_advanced`: date filter, symbol filter, annotation filter requires primary filter (400 path), pagination defaults, user isolation
- [x] 10.4 Add tests for `sync_trade_metadata`: notes update, taxonomy replace-all, annotation upsert, max-50 enforcement, non-owned IDs silently skipped
- [x] 10.5 Add tests for `create_strategy_playbook`: full creation, duplicate name returns error, rules formatted as markdown bullets
- [x] 10.6 Add test for `tools/call` with unknown tool name: verify `-32601` error response


## 11. Readme and docs
- [x] 11.1 Update `docs/mcp-client-integeration.md` with usage section with listing the four tool use cases as bullet points with example prompts
