## 1. Database migration (content consolidation)

- [x] 1.1 Create an Alembic migration (down_revision = current head) that runs `UPDATE playbooks SET description = content_markdown;` then `op.drop_column("playbooks", "content_markdown")`.
- [x] 1.2 Implement `downgrade()` re-adding `content_markdown` as nullable `Text` (document in the docstring that legacy `description` data is not recoverable).
- [x] 1.3 Apply and verify the migration using the `db-migration` skill (upgrade + downgrade round-trip on a scratch DB).

## 2. Backend model, schema, repository

- [x] 2.1 Remove the `content_markdown` column from `app/models/playbook.py`; keep `description` as unbounded `Text` and update the model docstring.
- [x] 2.2 In `app/schemas/playbook.py`, remove `content_markdown` from `PlaybookCreate`, `PlaybookUpdate`, `PlaybookRead`; remove the `max_length=PLAYBOOK_DESCRIPTION_MAX_LENGTH` cap from `description` and update field docs/examples.
- [x] 2.3 Remove `PLAYBOOK_DESCRIPTION_MAX_LENGTH` from `app/core/constants.py` if it becomes unused (otherwise leave it).
- [x] 2.4 Update `app/repositories/playbook_repository.py` create/update paths to stop referencing `content_markdown`.

## 3. MCP: playbook content consolidation

- [x] 3.1 In `app/api/mcp.py`, collapse `CreateStrategyPlaybookParams` / `UpdateStrategyPlaybookParams` to a single optional `description: str` (Markdown); remove the `rules` list and its bullet-serialization.
- [x] 3.2 Update `_handle_create_strategy_playbook` and `_handle_update_strategy_playbook` to write `description` directly (no `content_markdown`).
- [x] 3.3 Update `_handle_get_strategy_playbook` and `_handle_list_strategy_playbooks` to return `description` (drop `content_markdown`) AND include each playbook's assigned taxonomies (via `PlaybookTaxonomyService.list`), consistent with how `list_checkins` returns taxonomy assignments.
- [x] 3.4 Add an optional `taxonomy_ids: list[uuid.UUID] | None` param to `UpdateStrategyPlaybookParams`; when supplied, apply the shared additive tag helper (task 4.1) inside `_handle_update_strategy_playbook`. When omitted, leave assignments unchanged.
- [x] 3.5 Update the affected entries in `_TOOL_REGISTRY` (`inputSchema` + descriptions) to match the new params, including `taxonomy_ids` on `update_strategy_playbook` and taxonomies in the get/list output docs.

## 4. MCP: sync_playbook_metadata (additive tags, consistent with sync_*)

- [x] 4.1 Implement a shared async helper `_apply_playbook_taxonomies(db, user_id, playbook_id, taxonomy_ids)` that: verifies playbook ownership; validates the whole list (owned, non-archived, `scope_contains(scope, "playbook")`) failing atomically on any invalid id; then upserts each link via `pg_insert(PlaybookTaxonomy).on_conflict_do_nothing(constraint="uq_playbook_taxonomy_pair")` — mirroring the `sync_trade_metadata` insert loop. Reused by both `sync_playbook_metadata` and the `update_strategy_playbook` `taxonomy_ids` path (task 3.4).
- [x] 4.2 Add `SyncPlaybookMetadataParams` (`playbook_id: uuid.UUID`, `taxonomy_ids: list[uuid.UUID]`), matching the `Sync*MetadataParams` style.
- [x] 4.3 Add `_handle_sync_playbook_metadata` that calls the shared helper, flushes, and returns `{"updated_count": <n>}` (mirroring `sync_trade_metadata` / `sync_checkin_metadata`).
- [x] 4.4 Emit a safe audit event `playbook.bulk_metadata_synced` (safe identifiers + taxonomy count only), matching the `*.bulk_metadata_synced` pattern of the existing sync handlers.
- [x] 4.5 Register `sync_playbook_metadata` in `_TOOL_REGISTRY` (`mutating: True`) with `inputSchema` and a description mirroring `sync_checkin_metadata`. No standalone list/remove tool — reads come via get/list_strategy_playbook (task 3.3); removal stays REST-only.

## 5. Frontend

- [x] 5.1 Run the `openapi-sync` skill to regenerate the TypeScript client from the updated FastAPI spec.
- [x] 5.2 Update `components/playbooks/PlaybookEditorClient.tsx` to bind the editor state and save payload to `description` (remove `content_markdown` references).
- [x] 5.3 Confirm `PlaybookList.tsx` and any other playbook consumers still typecheck against the new client.

## 6. Tests

- [x] 6.1 Update `backend/tests/test_playbook_service.py` and `test_playbook_ownership.py` for the consolidated `description` field.
- [x] 6.2 Update `backend/tests/test_mcp_api.py` (`tools/list` count + playbook tool params) and add coverage for `sync_playbook_metadata` (additive/idempotent, scope rejection, archived/invalid rejection, not-found), taxonomies appearing in get/list_strategy_playbook output, and the `taxonomy_ids` path of `update_strategy_playbook`.
- [x] 6.3 Update `backend/tests/test_playbook_taxonomies_api.py` / `test_mcp_metadata_integration.py` as needed.
- [x] 6.4 Add/adjust a frontend test for the playbook editor binding to `description`.

## 7. Verification and documentation

- [x] 7.1 Run the `lint-check` skill (ruff + `mypy --strict`) and the `unit-test` skill (pytest with coverage); fix any failures.
- [x] 7.2 Update `AGENTS.md` / `docs/api-usage.md` if they reference the playbook `content_markdown` field or MCP `rules`.
- [x] 7.3 Append the change to the `[Unreleased]` section of `CHANGELOG.md` (mark the breaking API/MCP contract change).
