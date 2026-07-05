## Why

MCP clients (e.g. Claude Desktop, Cursor) can already read taxonomies and annotation definitions via `get_metadata_schema`, but cannot create, update, or delete them. This forces users to switch to the web UI for schema management, breaking AI-driven workflows where an agent needs to set up or evolve the metadata schema without human intervention.

## What Changes

- New MCP tool: `create_taxonomy` — create a taxonomy with name, scope, color, icon, description
- New MCP tool: `update_taxonomy` — update name, color, icon, description; archive/unarchive
- New MCP tool: `delete_taxonomy` — archive or force-delete a taxonomy
- New MCP tool: `create_annotation_definition` — create an annotation definition with name, type, scope, range/enum options
- New MCP tool: `update_annotation_definition` — update metadata and options; archive/unarchive
- New MCP tool: `delete_annotation_definition` — archive or force-delete an annotation definition
- Existing `get_metadata_schema` tool remains unchanged (read path)
- Existing UI (TaxonomyManager, AnnotationManager) remains fully functional — no removals

## Capabilities

### New Capabilities

- `mcp-taxonomy-crud`: MCP tools for creating, updating, and deleting taxonomy definitions (tags)
- `mcp-annotation-definition-crud`: MCP tools for creating, updating, and deleting annotation definition schemas

### Modified Capabilities

- `mcp-integration`: Two additional write tools are added to the MCP tool registry (schema-compatible extension, no breaking changes)

## Impact

- `backend/app/api/mcp.py` — add 6 new tool registrations and handlers
- `backend/app/services/taxonomy_service.py` — reused; no changes expected
- `backend/app/services/annotation_definition_service.py` — reused; no changes expected
- Frontend: no changes
- OpenAPI spec: no changes (MCP endpoint is not OpenAPI-documented)
- PAT auth: no changes (all MCP tools use existing PAT authentication)
