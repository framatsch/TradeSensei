## Context

The MCP server (`backend/app/api/mcp.py`) is a hand-rolled JSON-RPC 2.0 implementation with a `_TOOL_REGISTRY` mapping tool names to async `_handle_*` functions. It supports Streamable HTTP (`POST /mcp`) and legacy SSE, authenticated by PAT with Postgres row-level security. Every tool result is currently wrapped as a single `{"type": "text"}` MCP content block in `_dispatch_jsonrpc` (mcp.py:1791).

Relevant data model facts:
- `trade.image_urls` (JSONB) stores **storage refs** (`bucket/key`), not directly fetchable URLs. Same for `playbook_attachments.storage_url` and `daily_checkins.screenshot_urls`.
- `StorageService.generate_presigned_get_url(storage_ref)` converts a ref into a time-limited downloadable URL (existing pattern in `schemas/trade.py:1071`, `schemas/playbook_attachment.py:64`, `schemas/daily_checkin.py:187`).
- Trade "quick notes" (frontend `QuickNoteInput` → `useAddNote`) are rows in the `trade_notes` table, served by `NoteService.add_note()` / `list_notes()` (`note_service.py:65,48`). The single `trade.notes` Text field is a separate concept. **Ordering note:** the `quick-notes-workflow` change renames this table/model/service (`trade_notes` → `quick_notes`, `TradeNote*` → `QuickNote*`, `NoteService` → `QuickNoteService`). If that change lands first, this change MUST target the renamed identifiers; the MCP tool-facing surface (tool names, the `quick_notes` JSON key) is already consistent and does not change.
- `StorageService` has `upload_file_content` and `delete_file_by_storage_ref` but **no download/get-bytes** method.

## Goals / Non-Goals

**Goals:**
- Enable loading a single trade, check-in, taxonomy, or annotation definition by ID over MCP.
- Embed a trade's quick notes inline in `get_trade`, and allow adding, editing, and deleting quick notes via MCP.
- Allow editing the trade's main journal `notes` field (replace or append) on a single trade via MCP.
- Let a vision model actually see a trade's / playbook's chart images by returning image bytes as MCP image content blocks.
- Allow setting/clearing a trade's linked playbook over MCP.
- Keep all existing MCP tools and payload shapes 100% backward compatible.
- Protect the model context window from large or numerous images.

**Non-Goals:**
- No new upload path over MCP (images continue to be uploaded via existing REST endpoints).
- No embedding of binary attachments inside `get_*` metadata tools (kept lean and separate on purpose).
- No changes to authentication, RLS, transports, or the check-in/playbook write surfaces beyond the linking and note tools listed.
- No migration to an off-the-shelf MCP SDK.

## Decisions

### D1: Separate attachment tools instead of embedding binaries in `get_*`
`get_trade` / `get_checkin` / `get_strategy_playbook` return lightweight metadata only (including image **ref count + filenames**, not bytes). Actual binaries come from dedicated `get_trade_attachments` / `get_playbook_attachments` tools.
**Rationale:** Embedding base64 images in every metadata read would balloon the context window even when the caller only needs field values. Separation makes binary fetch an explicit, opt-in step. *(Alternative — always embed — rejected for context cost.)*

### D2: Default to base64 image content blocks, with a `url` escape hatch
`get_trade_attachments` / `get_playbook_attachments` take `format: "image" | "url"` (default `"image"`). `"image"` returns MCP `{"type":"image","data":<base64>,"mimeType":...}` blocks so the vision model sees the chart in the same turn; `"url"` returns presigned GET URLs as text for lean, link-only workflows.
**Rationale:** The primary use case ("look at the chart") requires the model to receive the image; the URL mode preserves a cheap option and reuses the existing presigned-URL path. *(Alternative — URL-only — rejected: many MCP hosts do not auto-fetch URLs into vision.)*

### D3: Content-block passthrough in dispatch
`_dispatch_jsonrpc` is extended so a handler may return a sentinel `{"_mcp_content": [...blocks...]}`. When present, those blocks are used verbatim as the `tools/call` result content; otherwise the existing single-text-block wrapping applies.
**Rationale:** Minimal, localized change that unlocks image blocks without touching any existing handler's return contract. *(Alternative — special-casing tool names in the dispatcher — rejected as brittle.)*

### D4: New `StorageService.download_file_by_storage_ref()`
Adds a `get_object`-based method returning `(bytes, content_type)`, using `_s3_client_internal` (the same client used for `put_object`/`delete_object`).
**Rationale:** Needed to produce base64 blocks; mirrors the existing internal-client pattern and keeps storage concerns in the storage layer.

### D5: Reuse the quick-note service; reuse `TradeService.update_trade` for journal edits
`add_trade_note` / `update_trade_note` / `delete_trade_note` delegate to the existing quick-note service (`add_note` / `update_note` / `delete_note`); `get_trade` embeds notes via its list method. The `update_trade_journal` tool edits the single `trade.notes` field via the existing trade update path (`TradeService.update_trade` with a `TradeUpdate(notes=...)`), reading the current value first for `append` mode. No new service or repository.
**Rationale:** Both services already enforce trade+user scoping and return typed DTOs; adding parallel paths would duplicate logic. `update_trade_journal` deliberately targets one trade, unlike the bulk overwrite-only `sync_trade_metadata`.
**Naming caveat:** the quick-note service is `NoteService` today. The `quick-notes-workflow` change renames it to `QuickNoteService` (and `trade_notes` → `quick_notes`). Whichever change lands second MUST use the then-current identifier; the MCP tool names and response keys are unaffected either way.

### D8: Journal edit is single-trade with explicit replace/append
`update_trade_journal` operates on exactly one `trade_id` and exposes `mode: "replace" | "append"` (default `replace`). `append` concatenates onto existing `notes` with a separating newline.
**Rationale:** The existing `sync_trade_metadata` only overwrites `notes` in bulk, which is destructive and coarse. A single-trade tool with an append mode supports the "write the analysis back" workflow without clobbering prior journal content. *(Alternative — only extend `sync_trade_metadata` — rejected: no per-trade granularity, no append.)*

### D9: Tool-name split — `*_trade_note` (quick notes) vs. `*_trade_journal` (journal field)
Quick-note tools are named `add_trade_note` / `update_trade_note` / `delete_trade_note` and operate on the timestamped quick-note rows. The main journal `notes` field is edited only via `update_trade_journal`. These two note concepts never share a tool.
**Rationale:** Keeps the two distinct concepts unambiguous for the calling model. The `trade_note` tool names are retained even though `quick-notes-workflow` renames the backend model to `QuickNote` — the tool surface is a stable public contract and does not track internal model identifiers. *(Alternative — rename tools to `*_quick_note` — rejected to keep the MCP surface stable.)*

### D6: Context-safety guardrails
Two bounded constants: max attachment items per call (default ~4) and max inline image bytes (default ~5 MB). Requests exceeding `max_items` are truncated (with a note in the response); an individual image exceeding the byte cap falls back to a presigned URL block instead of base64.
**Rationale:** A trade with many/large charts must not exhaust the context window or the JSON-RPC payload.

### D7: User-scoping and audit consistency
All new reads filter by `user_id` (plus RLS). Mutating tools (`add_trade_note`, `link_trade_playbook`) emit audit events (`trade.note_added`, `trade.playbook_linked`) with safe metadata only — resource IDs, never note content, P&L, or other sensitive values — matching the existing handlers and the AGENTS.md audit policy.

## Risks / Trade-offs

- **Large/base64 payloads bloat context** → Mitigated by D6 (`max_items` + per-image byte cap with URL fallback) and D2 (`format:"url"`).
- **Storage backend unreachable or ref missing when downloading** → Handler catches storage errors per image and degrades to a URL/text block or an explicit error entry rather than failing the whole call.
- **Presigned URL expiry** → Reuse existing `storage_presigned_get_ttl_seconds` (1h) / `storage_presigned_get_ttl_playbook_seconds` (4h); callers fetch promptly.
- **Ownership leakage across users** → All lookups are `user_id`-scoped and validated (e.g. `link_trade_playbook` verifies both trade and playbook belong to the caller) before any read/write.
- **Dispatch passthrough regressions** → The sentinel key is opt-in; existing handlers are untouched, and tests assert both text and image result shapes.

## Migration Plan

Additive, no schema or data migration. Deploy backend with the new tools; MCP clients discover them via `tools/list`. Rollback = revert the `mcp.py` / `storage_service.py` changes; no persisted state is introduced.

## Cross-Change Dependency

The `quick-notes-workflow` change renames the quick-note table/model/schemas/service from `trade_notes`/`TradeNote*`/`NoteService` to `quick_notes`/`QuickNote*`/`QuickNoteService`. This MCP change reuses that service and reads that collection, so the two overlap on identifiers.

- **This change does NOT perform the rename** — it only consumes the quick-note store.
- If `quick-notes-workflow` is implemented **first**, this change's implementation MUST reference the renamed identifiers (`QuickNoteService`, `quick_notes` relationship).
- If this change is implemented **first**, it references the current `NoteService`/`trade_notes`, and `quick-notes-workflow` will later rename them (its tasks already cover repository/service call sites).
- Either way the MCP tool names (`get_trade`, `add_trade_note`) and the `quick_notes` JSON response key are already consistent and require no change.

## Open Questions

None outstanding — transport default (`format:"image"`) and note embedding (`quick_notes` inside `get_trade`) were confirmed during proposal discussion. Identifier ordering vs. `quick-notes-workflow` is captured under Cross-Change Dependency above.
