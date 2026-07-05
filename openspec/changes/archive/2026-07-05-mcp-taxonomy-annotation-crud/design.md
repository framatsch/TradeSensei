## Context

The MCP server at `backend/app/api/mcp.py` exposes a JSON-RPC 2.0 interface over SSE, authenticated via Personal Access Tokens. It already has read/write tools for trades, check-ins, playbooks, and portfolios. Taxonomy and annotation definition management is read-only via `get_metadata_schema`, which returns active definitions but provides no way to create or modify them.

The service and repository layers for both taxonomies (`TaxonomyService`, `TaxonomyRepository`) and annotation definitions (`AnnotationDefinitionService`, `AnnotationDefinitionRepository`) are fully implemented and tested. The corresponding Pydantic schemas (`TaxonomyCreate`, `TaxonomyUpdate`, `AnnotationDefinitionCreate`, `AnnotationDefinitionUpdate`) are already in place.

## Goals / Non-Goals

**Goals:**
- Add 6 new MCP tools by wiring existing service methods into the `_TOOL_REGISTRY` in `mcp.py`
- Follow the existing tool handler pattern (Pydantic params model → service call → audit event → return dict)
- Emit audit events for all write operations (same pattern as playbook tools)
- Keep all changes confined to `backend/app/api/mcp.py` — no new files, no service changes

**Non-Goals:**
- Modifying the web UI (no frontend changes)
- Adding archive/restore to `get_metadata_schema` output (read path unchanged)
- Changing the PAT auth mechanism
- Adding pagination to list tools (service already handles this without it)

## Decisions

**Reuse service layer directly** — `TaxonomyService` and `AnnotationDefinitionService` already encapsulate all validation (name uniqueness, color_hex format, scope tokens). The MCP handlers delegate to them rather than duplicating validation logic.

**No separate "list" tools for taxonomy/annotation** — `get_metadata_schema` already returns all active definitions. Adding `list_taxonomies` / `list_annotation_definitions` would duplicate this. If a complete list including archived items is needed, it can be a future addition.

**Delete = archive only via MCP** — MCP tools call `TaxonomyService.archive` / `AnnotationDefinitionService.archive` directly. The `force` hard-delete path is deliberately not exposed: it permanently removes all assignment history without any confirmation mechanism equivalent to the UI's "type the name" danger zone. If a taxonomy has active assignments, the tool returns an error prompting the caller to remove assignments first. Hard-delete remains UI-exclusive where an explicit confirmation step prevents accidental data loss.

**Pydantic params models inline in mcp.py** — all existing MCP tool params models are defined in `mcp.py`. New models follow the same convention to keep the file self-contained.

**Audit events** — use `"taxonomy.created"`, `"taxonomy.updated"`, `"taxonomy.deleted"`, `"annotation_definition.created"`, `"annotation_definition.updated"`, `"annotation_definition.deleted"` following the `<resource>.<verb>` naming convention. Safe metadata: `user_id`, `taxonomy_id` or `annotation_definition_id`.

## Risks / Trade-offs

**File length** — `mcp.py` is already large (~1200 lines). Adding ~200 more lines increases it but stays manageable. A future refactor could split it into sub-modules, but that is out of scope here.

**Force-delete race condition** — not applicable; force-delete is not exposed via MCP. Archive is idempotent and safe.
