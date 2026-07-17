## Context

The `playbooks` table has two content columns:

- `description` — `Text`, capped at `PLAYBOOK_DESCRIPTION_MAX_LENGTH = 2000` in schemas, created in migration `0003_playbook_tags_notes`.
- `content_markdown` — `Text`, added later in migration `9f3772f33761`.

Only `content_markdown` is written by the UI (`PlaybookEditorClient.tsx`) and is the field the MCP `rules` list is serialized into (`app/api/mcp.py` `_handle_create_strategy_playbook` / `_handle_update_strategy_playbook`). `description` is a required field on every Pydantic schema but carries no live UI meaning. This produces two near-synonymous fields and a confusing MCP contract where `rules` (→ `content_markdown`) and `description` are separate params.

Separately, taxonomy assignment to playbooks exists only as REST (`app/api/v1/playbook_taxonomies.py` → `PlaybookTaxonomyService`). The MCP server (`app/api/mcp.py`) has playbook CRUD tools but no tool to attach/detach a taxonomy, so an MCP client cannot fully manage a playbook.

Constraints: `mypy --strict`, Alembic-only schema changes, audit-logging policy (safe identifiers only), MCP secured by PAT with Postgres RLS via `SET LOCAL app.current_user_id`.

## Goals / Non-Goals

**Goals:**
- Collapse playbook content to a single `description` (unbounded `Text`, Markdown), where `content_markdown` overwrites `description` during migration.
- Remove `content_markdown` from model, schemas, repository, MCP tools, and frontend.
- Add MCP tools to assign, list, and remove taxonomies on a playbook, reusing `PlaybookTaxonomyService`.
- Regenerate the OpenAPI client and update the playbook editor.

**Non-Goals:**
- No change to the REST playbook-taxonomy endpoints (they already work; MCP simply reuses the service).
- No change to taxonomy scope semantics or the `taxonomies` table.
- No new "rules"-as-structured-list model; `rules` is folded into free-form Markdown `description`.
- No backfill/repair of the pre-existing DB-vs-app scope-constraint divergence (out of scope).

## Decisions

**D1 — content_markdown always overwrites description (per user instruction).**
The migration sets `description = content_markdown` for all rows unconditionally, then drops `content_markdown`. Chosen over a "coalesce" strategy because the UI/MCP have only ever populated `content_markdown`, so it is the single source of truth; any stale `description` text is obsolete. Alternative (keep description when content_markdown is null) rejected: it would resurrect stale legacy text the user considers dead.

**D2 — Keep the surviving column named `description`, drop `content_markdown`.**
Renaming `content_markdown` → `description` would require first dropping the old `description`; a data copy + `DROP COLUMN content_markdown` is simpler and keeps the externally-familiar field name `description`. The API field `description` is retained (semantics change to Markdown), minimizing renames across schemas and clients.

**D3 — Remove the 2000-char cap.**
`PLAYBOOK_DESCRIPTION_MAX_LENGTH` is dropped from the create/update schemas so `description` is unbounded Markdown (backed by `Text`). The constant is removed if unused elsewhere, otherwise left untouched.

**D4 — MCP tags follow the existing `sync_<entity>_metadata` convention exactly.**
Trades and check-ins do not expose per-tag verbs or a dedicated list/remove tag tool. Their entire metadata-assignment surface is a single bulk tool — `sync_trade_metadata` / `sync_checkin_metadata` — that takes a `taxonomy_ids` list and additively upserts with `on_conflict_do_nothing` (never removing), returning an `updated_count`. Assigned tags are surfaced on the read side (`list_checkins` "Returns taxonomy and annotation assignments per check-in").

Per user decision, the playbook tool mirrors this convention: **`sync_playbook_metadata(playbook_id, taxonomy_ids[])`**, additive/idempotent, returning an updated count. Rationale over the earlier `set_playbook_taxonomies` + `list_playbook_taxonomies` proposal: it matches the established MCP metadata naming/shape, and — like trades/checkins — needs no standalone list or remove tool. Removal remains available via the REST API. Single `playbook_id` (not `playbook_ids[]`) is used because playbooks are edited individually and the existing playbook tools are already singular; this is the one intentional shape deviation from the bulk `*_ids` list.

**D5 — Assigned taxonomies are surfaced on the playbook read tools, not a dedicated list tool.**
`get_strategy_playbook` and `list_strategy_playbooks` are extended to include each playbook's assigned taxonomies, consistent with `list_checkins`. This replaces the previously-proposed `list_playbook_taxonomies` tool.

**D6 — Validation: owned + non-archived + playbook scope (stricter than `sync_trade/checkin_metadata`).**
`sync_trade_metadata` / `sync_checkin_metadata` validate only that taxonomies are owned and non-archived; they do **not** check taxonomy scope. Per user decision, `sync_playbook_metadata` additionally enforces `scope_contains(scope, "playbook")` — matching the REST `PlaybookTaxonomyService` — to prevent attaching non-playbook-scoped tags. This is a deliberate, documented deviation from the two existing sync tools, made for correctness. Validation runs over the entire `taxonomy_ids` list before any insert, so one invalid id fails the whole call atomically.

**D7 — `update_strategy_playbook` gains an optional `taxonomy_ids` param, sharing one helper.**
Per user decision, `update_strategy_playbook` accepts an optional `taxonomy_ids` list so content and tags can be set in one call. A shared internal helper (validate list → additive `pg_insert(...).on_conflict_do_nothing`) is used by both `sync_playbook_metadata` and this update path, guaranteeing identical semantics and validation. When `taxonomy_ids` is omitted, assignments are untouched. The reads (D5) use `PlaybookTaxonomyService.list` for retrieval.

**D5 — MCP playbook param models collapse `rules`/`description`/`content_markdown` into `description`.**
`CreateStrategyPlaybookParams` / `UpdateStrategyPlaybookParams` expose a single optional `description: str` (Markdown). The `rules: list[str]` → bullet-serialization logic is removed. `get`/`list` handlers return `description` only (no `content_markdown`). This is a breaking MCP contract change, documented in the proposal.

## Risks / Trade-offs

- **Data loss of legacy `description` text** → Accepted per D1/user instruction; documented in migration docstring. Down-migration re-adds an empty `content_markdown` column (cannot recover dropped data) — acceptable, noted explicitly.
- **Breaking API/MCP contract** (`content_markdown` removed, `description` now Markdown/unbounded, MCP `rules` removed) → Mitigation: single coordinated change; regenerate OpenAPI client; update all tests in the same PR. This is an internal, self-hosted app, so no external consumer contract to preserve.
- **MCP tool count/registry drift** → Mitigation: add registry entries + `inputSchema` next to existing playbook tools; extend `test_mcp_api.py` `tools/list` assertions.
- **RLS scoping for new MCP handlers** → Mitigation: use the same `_get_mcp_session_with_rls` path as existing handlers so `app.current_user_id` is set before service calls.

## Migration Plan

1. Add Alembic migration (down_revision = current head):
   - `UPDATE playbooks SET description = content_markdown;`
   - `op.drop_column("playbooks", "content_markdown")`.
   - `downgrade()`: `op.add_column("playbooks", sa.Column("content_markdown", sa.Text(), nullable=True))` (data not restorable).
2. Update model, schemas, repository; remove `content_markdown` and the length cap.
3. Update MCP param models + playbook handlers; add taxonomy-assignment handlers + registry entries.
4. Run `db-migration` skill to apply + verify; run `lint-check` and `unit-test`.
5. Run `openapi-sync` to regenerate the frontend client; update `PlaybookEditorClient.tsx`.
6. Rollback: `alembic downgrade -1` re-adds an empty `content_markdown`; revert code. Legacy description text is not recoverable — communicate before deploy.

## Open Questions

- None blocking. The 2000-char removal (D3) and unconditional overwrite (D1) are confirmed by the user's instruction ("immer description mit content_markdown überschrieben").
