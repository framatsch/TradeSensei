## Why

The MCP interface today is collection- and bulk-oriented: trades, check-ins, taxonomies, and annotation definitions can only be searched or bulk-mutated, never loaded individually by ID, and their attached chart images/screenshots are never exposed. This blocks natural single-resource prompts like *"load trade 1234 and link it to playbook xyz"* and, critically, vision workflows like *"analyse trade XYZ, look at the chart I uploaded, check it against the linked playbook, and write the result back as a trade note"* — because the model can neither fetch a single trade nor see its chart binary.

## What Changes

- Add **get-by-ID read tools**: `get_trade`, `get_checkin`, `get_taxonomy`, `get_annotation_definition`. `get_trade` embeds the trade's timestamped quick notes inline.
- Add **quick-note write tools**: `add_trade_note` (append a timestamped note with content + optional emotion), `update_trade_note` (edit an existing note's content/emotion), and `delete_trade_note` (remove a note), reusing the existing quick-note service.
- Add a **journal edit tool** `update_trade_journal` that sets (`replace`) or appends (`append`) to a single trade's main journal `notes` field — distinct from the timestamped quick notes and finer-grained than the existing bulk `sync_trade_metadata`.
- Add **binary attachment tools** `get_trade_attachments` and `get_playbook_attachments` that return the actual image bytes as base64 MCP image content blocks (default `format:"image"`, with a `format:"url"` presigned-URL escape hatch), guarded by `max_items` and per-image size caps to protect the context window.
- Add a **trade↔playbook linking tool** `link_trade_playbook` that sets or clears `trade.playbook_id`.
- Extend the MCP dispatch layer so tool handlers can emit non-text content blocks (image blocks) while all existing text-returning tools remain unchanged (backward compatible).
- Add a binary download helper `StorageService.download_file_by_storage_ref()` to fetch object bytes for the attachment tools.

## Capabilities

### New Capabilities
- `mcp-resource-loaders`: Single-resource get-by-ID MCP tools for trades (with embedded quick notes), check-ins, taxonomies, and annotation definitions.
- `mcp-trade-notes`: MCP tools to add, edit, and delete a trade's timestamped quick notes, and to edit (replace/append) the trade's main journal `notes` field.
- `mcp-attachment-download`: MCP tools returning trade and playbook image attachments as base64 image content blocks or presigned URLs, with context-safety guardrails.
- `mcp-trade-playbook-link`: MCP tool to set or clear a trade's linked playbook.

### Modified Capabilities
<!-- No existing spec-level requirements change; all additions are net-new capabilities. -->

## Impact

- **Code**: `backend/app/api/mcp.py` (new param models, handlers, registry entries, content-block plumbing in `_dispatch_jsonrpc`); `backend/app/services/storage_service.py` (new `download_file_by_storage_ref`); reuse of the quick-note service (`NoteService`, renamed to `QuickNoteService` by the `quick-notes-workflow` change), `StorageService.generate_presigned_get_url`, and existing presigned-GET TTL settings.
- **Config**: new bounded constants for max attachment items and max inline image bytes.
- **Tests**: `backend/tests/test_mcp_api.py` extended; new storage-service unit test.
- **Docs**: `docs/api-usage.md` and `CHANGELOG.md` `[Unreleased]`.
- **Security/Audit**: mutating tools (`add_trade_note`, `link_trade_playbook`) emit audit events with safe metadata only (resource IDs, no note content or monetary values); all reads remain user-scoped under existing PAT + row-level security.
- **No breaking changes**: existing MCP tools, transports, and payload shapes are untouched.
- **Cross-change ordering**: overlaps with `quick-notes-workflow`, which renames `trade_notes`/`TradeNote*`/`NoteService` → `quick_notes`/`QuickNote*`/`QuickNoteService`. This change consumes that store but does not perform the rename; whichever change lands second uses the then-current identifiers. MCP tool names and the `quick_notes` JSON key are consistent regardless. See design.md → Cross-Change Dependency.
