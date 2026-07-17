## Why

The `playbooks` table carries two overlapping content columns: `description` (Text, capped at 2000 chars) and `content_markdown` (Text, added later). The UI (`PlaybookEditorClient.tsx`) and the MCP `rules` concept only ever write `content_markdown`; the original `description` column is effectively dead weight but still a required field across every schema and the MCP tool surface. This duplication causes confusion (two "description-like" fields), a needless length cap, and a divergent MCP contract where `rules` and `description` are separate. Consolidating to a single markdown field removes the ambiguity.

Separately, tags (taxonomies) can currently only be assigned to a playbook through the REST API. The MCP server already exposes playbook create/update/get/list tools but has **no** way to attach or detach a taxonomy from a playbook, so an MCP client cannot fully manage a playbook's metadata.

## What Changes

- **BREAKING** — Consolidate playbook content into a single `description` column:
  - Migrate data: for every playbook, `content_markdown` overwrites `description` (content_markdown always wins), then drop the old `content_markdown` column.
  - The surviving `description` column becomes the long-form Markdown field (the 2000-char cap is removed; it is now unbounded `Text`).
  - Remove `content_markdown` from all Pydantic schemas (`PlaybookCreate`, `PlaybookUpdate`, `PlaybookRead`) and from the repository create/update paths.
  - **BREAKING** — MCP `create_strategy_playbook` / `update_strategy_playbook` / `get_strategy_playbook` / `list_strategy_playbooks` collapse the separate `rules`/`description`/`content_markdown` fields into a single `description` (Markdown) field.
- Add MCP tag support for playbooks, consistent with the existing `sync_trade_metadata` / `sync_checkin_metadata` convention:
  - New `sync_playbook_metadata(playbook_id, taxonomy_ids[])` tool — additive/idempotent upsert (never removes), returning an `updated_count`. Validation enforces owned + non-archived + `scope_contains(scope, "playbook")`.
  - `update_strategy_playbook` gains an optional `taxonomy_ids` param (shares one helper with `sync_playbook_metadata`) so content and tags can be set in one call.
  - `get_strategy_playbook` / `list_strategy_playbooks` include each playbook's assigned taxonomies (like `list_checkins`) — no standalone list/remove tool; removal stays REST-only.
- Regenerate the frontend OpenAPI client and update `PlaybookEditorClient.tsx` to bind the editor to `description`.

## Capabilities

### New Capabilities
- `playbook-content-model`: The consolidated single-field content model for playbooks (`description` as unbounded Markdown), including the data-migration rule that `content_markdown` overwrites `description`.
- `mcp-playbook-tag-assignment`: MCP support for setting taxonomy tags on a playbook via `sync_playbook_metadata` and via an optional `taxonomy_ids` param on `update_strategy_playbook`, plus surfacing assigned taxonomies on the playbook read tools — consistent with the `sync_*_metadata` convention.

### Modified Capabilities
<!-- No live spec in openspec/specs/ owns the playbook content model or MCP playbook tools; both are introduced as new capabilities above. -->

## Impact

- **Database**: Alembic migration — data copy (`content_markdown` → `description`) then `DROP COLUMN content_markdown`. Down-migration restores the column (data loss on downgrade is acceptable and documented).
- **Backend models/schemas/repos**: `app/models/playbook.py`, `app/schemas/playbook.py`, `app/repositories/playbook_repository.py`, `app/core/constants.py` (`PLAYBOOK_DESCRIPTION_MAX_LENGTH` removed or repurposed).
- **MCP**: `app/api/mcp.py` — playbook param models + `_handle_*_strategy_playbook` handlers updated (content consolidation, `taxonomy_ids` on update, taxonomies in get/list output); new `SyncPlaybookMetadataParams` + `_handle_sync_playbook_metadata` + shared tag helper + tool-registry entry.
- **API contract**: `PlaybookRead` loses `content_markdown`; `description` semantics change (now Markdown, unbounded). Breaking for external REST/MCP consumers.
- **Frontend**: regenerated OpenAPI client + `components/playbooks/PlaybookEditorClient.tsx`.
- **Tests**: `test_playbook_service.py`, `test_playbook_ownership.py`, `test_playbook_taxonomies_api.py`, `test_mcp_api.py`, `test_mcp_metadata_integration.py`.
- **Audit logging**: reuses existing middleware + MCP audit events; new MCP tag handlers emit `playbook.updated`-style audit events with safe identifiers only.
