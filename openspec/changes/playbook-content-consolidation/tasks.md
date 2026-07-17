## 1. Database migration (content consolidation)

- [ ] 1.1 Create an Alembic migration (down_revision = current head) that runs `UPDATE playbooks SET description = content_markdown;` then `op.drop_column("playbooks", "content_markdown")`.
- [ ] 1.2 Implement `downgrade()` re-adding `content_markdown` as nullable `Text` (document in the docstring that legacy `description` data is not recoverable).
- [ ] 1.3 Apply and verify the migration using the `db-migration` skill (upgrade + downgrade round-trip on a scratch DB).

## 2. Backend model, schema, repository

- [ ] 2.1 Remove the `content_markdown` column from `app/models/playbook.py`; keep `description` as unbounded `Text` and update the model docstring.
- [ ] 2.2 In `app/schemas/playbook.py`, remove `content_markdown` from `PlaybookCreate`, `PlaybookUpdate`, `PlaybookRead`; remove the `max_length=PLAYBOOK_DESCRIPTION_MAX_LENGTH` cap from `description` and update field docs/examples.
- [ ] 2.3 Remove `PLAYBOOK_DESCRIPTION_MAX_LENGTH` from `app/core/constants.py` if it becomes unused (otherwise leave it).
- [ ] 2.4 Update `app/repositories/playbook_repository.py` create/update paths to stop referencing `content_markdown`.

## 3. MCP: playbook content consolidation

- [ ] 3.1 In `app/api/mcp.py`, collapse `CreateStrategyPlaybookParams` / `UpdateStrategyPlaybookParams` to a single optional `description: str` (Markdown); remove the `rules` list and its bullet-serialization.
- [ ] 3.2 Update `_handle_create_strategy_playbook` and `_handle_update_strategy_playbook` to write `description` directly (no `content_markdown`).
- [ ] 3.3 Update `_handle_get_strategy_playbook` and `_handle_list_strategy_playbooks` to return `description` only (drop `content_markdown`).
- [ ] 3.4 Add an optional `taxonomy_ids: list[uuid.UUID] | None` param to `UpdateStrategyPlaybookParams`; when supplied, apply the same additive, scope-enforced, archived-rejecting tag logic as the dedicated set tool (see 4.x) within `_handle_update_strategy_playbook`. When omitted, leave assignments unchanged.
- [ ] 3.5 Update the affected entries in `_TOOL_REGISTRY` (`inputSchema` + descriptions) to match the new params, including `taxonomy_ids` on `update_strategy_playbook`.

## 4. MCP: playbook tag tools (set + list, additive)

- [ ] 4.1 Add a Pydantic param model `SyncPlaybookTaxonomiesParams` (or similarly named) with `playbook_id` and `taxonomy_ids: list[uuid.UUID]`; add a list param model with `playbook_id`.
- [ ] 4.2 Implement a shared helper that additively upserts taxonomies onto a playbook: verify playbook ownership, validate every `taxonomy_id` (owned, non-archived, scope includes `playbook`) — mirroring `PlaybookTaxonomyService.assign` validation but for a list — then `pg_insert(PlaybookTaxonomy).on_conflict_do_nothing` per id (consistent with `sync_trade_metadata`). Reuse this helper from both the set tool and the `update_strategy_playbook` `taxonomy_ids` path (task 3.4).
- [ ] 4.3 Add `_handle_set_playbook_taxonomies` (additive set) and `_handle_list_playbook_taxonomies` (read via `PlaybookTaxonomyService.list`), translating service/validation errors to MCP tool errors.
- [ ] 4.4 Emit a safe audit event (`playbook.<verb>`, safe identifiers + taxonomy count only) for the mutating set handler, following the existing MCP audit-event pattern.
- [ ] 4.5 Register the set + list tools in `_TOOL_REGISTRY` with `inputSchema`, descriptions, and correct `mutating` flags. (No standalone remove tool — semantics are additive, consistent with `sync_*`.)

## 5. Frontend

- [ ] 5.1 Run the `openapi-sync` skill to regenerate the TypeScript client from the updated FastAPI spec.
- [ ] 5.2 Update `components/playbooks/PlaybookEditorClient.tsx` to bind the editor state and save payload to `description` (remove `content_markdown` references).
- [ ] 5.3 Confirm `PlaybookList.tsx` and any other playbook consumers still typecheck against the new client.

## 6. Tests

- [ ] 6.1 Update `backend/tests/test_playbook_service.py` and `test_playbook_ownership.py` for the consolidated `description` field.
- [ ] 6.2 Update `backend/tests/test_mcp_api.py` (`tools/list` count + playbook tool params) and add coverage for the set tool (additive/idempotent, scope rejection, archived/invalid rejection, not-found), the list tool, and the `taxonomy_ids` path of `update_strategy_playbook`.
- [ ] 6.3 Update `backend/tests/test_playbook_taxonomies_api.py` / `test_mcp_metadata_integration.py` as needed.
- [ ] 6.4 Add/adjust a frontend test for the playbook editor binding to `description`.

## 7. Verification and documentation

- [ ] 7.1 Run the `lint-check` skill (ruff + `mypy --strict`) and the `unit-test` skill (pytest with coverage); fix any failures.
- [ ] 7.2 Update `AGENTS.md` / `docs/api-usage.md` if they reference the playbook `content_markdown` field or MCP `rules`.
- [ ] 7.3 Append the change to the `[Unreleased]` section of `CHANGELOG.md` (mark the breaking API/MCP contract change).
