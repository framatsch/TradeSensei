## 1. Storage layer

- [x] 1.1 Add `download_file_by_storage_ref(storage_ref) -> tuple[bytes, str]` to `StorageService` using `_s3_client_internal.get_object`, returning bytes and content type
- [x] 1.2 Add a unit test for `download_file_by_storage_ref` (mocked S3 client) covering success and missing-object/error paths

## 2. Config constants

- [x] 2.1 Add bounded settings/constants for maximum attachment items per call (default ~4) and maximum inline image bytes (default ~5 MB) in the appropriate config/constants module

## 3. Dispatch content-block passthrough

- [x] 3.1 Extend `_dispatch_jsonrpc` in `backend/app/api/mcp.py` so a handler returning `{"_mcp_content": [...]}` yields those blocks verbatim as the `tools/call` result content, while all other handlers keep the existing single text-block wrapping
- [x] 3.2 Add a small helper to build MCP image content blocks (`{"type":"image","data":<base64>,"mimeType":...}`) and text blocks

## 4. Get-by-ID read tools (mcp-resource-loaders)

- [x] 4.1 Add param models `GetTradeParams`, `GetCheckinParams`, `GetTaxonomyParams`, `GetAnnotationDefinitionParams`
- [x] 4.2 Implement `_handle_get_trade`: user-scoped trade load with core fields, `notes`, `user_rating`, `tradingview_link`, `playbook_id`, taxonomy + annotation assignments, image ref count + filenames (no binary), and embedded `quick_notes` via the quick-note service list method (`NoteService.list_notes`, or `QuickNoteService` if `quick-notes-workflow` landed first)
- [x] 4.3 Implement `_handle_get_checkin`: user-scoped check-in load with full taxonomy + annotation assignment detail (typed values), news links, screenshot ref count
- [x] 4.4 Implement `_handle_get_taxonomy` and `_handle_get_annotation_definition`: single-record user-scoped loads
- [x] 4.5 Register all four tools in `_TOOL_REGISTRY` with `inputSchema` and `mutating: False`

## 5. Quick-note and journal write tools (mcp-trade-notes)

- [x] 5.1 Add `AddTradeNoteParams` (trade_id, content, optional emotion), `UpdateTradeNoteParams` (trade_id, note_id, optional content, optional emotion), `DeleteTradeNoteParams` (trade_id, note_id), and `UpdateTradeJournalParams` (trade_id, text, `mode: "replace"|"append"` default `replace`)
- [x] 5.2 Implement `_handle_add_trade_note` using the quick-note service add method (`NoteService.add_note`, or `QuickNoteService` if `quick-notes-workflow` landed first), with trade ownership validation and `trade.note_added` audit event (safe metadata: trade id, note id; no content)
- [x] 5.3 Implement `_handle_update_trade_note` using the service update method (`update_note`), scoping by trade_id + note_id + user, emitting `trade.note_updated` (safe metadata only)
- [x] 5.4 Implement `_handle_delete_trade_note` using the service delete method (`delete_note`), scoping by trade_id + note_id + user, emitting `trade.note_deleted` (safe metadata only)
- [x] 5.5 Implement `_handle_update_trade_journal`: load owned trade, for `append` read current `notes` and concatenate with a separating newline, persist via `TradeService.update_trade` (`TradeUpdate(notes=...)`), emit `trade.journal_updated` (safe metadata: trade id; no journal content)
- [x] 5.6 Register `add_trade_note`, `update_trade_note`, `delete_trade_note`, and `update_trade_journal` in `_TOOL_REGISTRY` with `mutating: True`

## 6. Attachment download tools (mcp-attachment-download)

- [x] 6.1 Add `GetTradeAttachmentsParams` and `GetPlaybookAttachmentsParams` (id, `format: "image"|"url"` default `image`, `max_items`)
- [x] 6.2 Implement `_handle_get_trade_attachments`: resolve `trade.image_urls` refs; `image` -> base64 image blocks via `download_file_by_storage_ref`, `url` -> presigned GET URLs; apply `max_items` truncation, per-image size cap with URL fallback, and per-image storage-error degradation
- [x] 6.3 Implement `_handle_get_playbook_attachments`: same image handling for playbook `attachments`, plus `links` (label + url) as text
- [x] 6.4 Return image results via the `_mcp_content` passthrough; register both tools in `_TOOL_REGISTRY` with `mutating: False`

## 7. Trade↔playbook link tool (mcp-trade-playbook-link)

- [x] 7.1 Add `LinkTradePlaybookParams` (trade_id, optional playbook_id, explicit clear semantics)
- [x] 7.2 Implement `_handle_link_trade_playbook`: validate trade and playbook ownership, set/clear `trade.playbook_id`, emit `trade.playbook_linked` audit event with safe metadata
- [x] 7.3 Register `link_trade_playbook` in `_TOOL_REGISTRY` with `mutating: True`

## 8. Tests

- [x] 8.1 Extend `backend/tests/test_mcp_api.py`: `tools/list` includes the new tools; get-by-ID success + not-found/isolation for trade, checkin, taxonomy, annotation definition
- [x] 8.2 Test `get_trade` embeds `quick_notes`; test `add_trade_note` creates a note and enforces ownership; test `update_trade_note` and `delete_trade_note` for success + cross-user/unknown-id rejection; test `update_trade_journal` in `replace` and `append` modes + ownership rejection
- [x] 8.3 Test `get_trade_attachments` in both `image` (base64 block, mime type) and `url` modes, empty-attachments case, `max_items` truncation, and oversized-image URL fallback
- [x] 8.4 Test `get_playbook_attachments` returns image blocks + links
- [x] 8.5 Test `link_trade_playbook` set, clear, and cross-user/unknown-id rejection paths

## 9. Verification, docs, changelog

- [x] 9.0 Cross-change consistency: check whether `quick-notes-workflow` has been applied; if so, reference the renamed identifiers (`QuickNoteService`, `quick_notes` table/relationship, `QuickNote*` schemas) instead of `NoteService`/`trade_notes` throughout this change's implementation
- [x] 9.1 Run lint-check (ruff + mypy --strict) and fix any issues in changed files
- [x] 9.2 Run the MCP and storage-service tests via pytest and ensure green
- [x] 9.3 Update `docs/api-usage.md` with the new MCP tools and example prompts (load trade + link playbook; analyse chart -> write note) — documented in `docs/mcp-client-integration.md` instead, the existing established home for MCP tool docs (see session notes)
- [x] 9.4 Add a `[Unreleased]` entry to `CHANGELOG.md` describing the new MCP tools
