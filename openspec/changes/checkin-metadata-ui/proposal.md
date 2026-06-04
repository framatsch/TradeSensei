# Proposal: checkin-metadata-ui

## Summary

Extend the Check-in Form and Filter Bar to support full Tag (Taxonomy) and Annotation management. Additionally extend the Trade and Workspace filter bars with the same generic Annotation Filter mechanism so users can correlate check-in state with trading performance.

## Problem

- The Check-in Form has no UI for assigning Tags (Taxonomy via the assign/remove endpoints) or for reading/setting Annotation values. The API and DB layer for both already exist.
- The Check-in Filter Bar cannot filter by taxonomy_ids or annotation values.
- The Trade and Workspace filter bars also lack annotation-based filtering despite the MCP endpoint demonstrating that the backend query logic already exists.

## Proposed Solution

### 1. Check-in Form — Taxonomy (Tags)

Add a multi-select Tags field below the existing Market Phase section. It uses the `POST /{checkin_id}/taxonomies` and `DELETE /{checkin_id}/taxonomies/{id}` endpoints to assign/remove tags (scope="checkins") from an existing check-in. For a new check-in the tag IDs are collected in local state and assigned in a post-save callback.

**Market Phase stays unchanged** — it remains a single-select pill field stored directly in `market_phase`. The new Tags field is a separate, additional UI element for general-purpose checkin taxonomies.

### 2. Check-in Form — Annotations

Add an Annotations section that renders a typed input per AnnotationDefinition with scope="checkins" (or scope="both"). Input type is determined by the definition's `type` field:

| type | UI element |
|---|---|
| bool | Toggle / Checkbox |
| string_enum | Dropdown (from `scale_labels`) |
| int | Number input (integer) |
| float | Number input (decimal) |

Values are saved via `POST /{checkin_id}/annotations/{annotation_definition_id}` and updated via `PUT /{checkin_id}/annotations/{annotation_definition_id}`. A clear button removes via `DELETE`.

### 3. Check-in Filter — taxonomy_ids + annotation_filters

Extend `CheckinFilterBar` and the backend `list_checkins` endpoint with:
- `taxonomy_ids`: multi-select (any of the selected tags must be assigned)
- `annotation_filters`: list of `{ annotation_definition_id, operator, value, logic }` where `logic` is AND/OR per filter entry

### 4. Generic Annotation Filter — Trades & Workspace

Extract the annotation filter logic already present in `mcp.py` into a shared utility (`app/repositories/_annotation_filter.py`) and expose it via the standard `GET /trades` and Workspace filter endpoints. Frontend: add an Annotation Filters multi-row UI section to `TradeFilterBar` and `WorkspaceFilterBar` with the same AND/OR toggle per row.

## Operator semantics

| type | allowed operators |
|---|---|
| bool | `eq` |
| string_enum | `eq`, `neq` |
| int | `eq`, `neq`, `gt`, `gte`, `lt`, `lte` |
| float | `eq`, `neq`, `gt`, `gte`, `lt`, `lte` |

Multiple annotation_filters are combined with AND by default. Each individual filter entry has an optional `logic: "AND" | "OR"` field that controls how it is combined with the *previous* entry in the list (first entry ignores this field).

## Out of scope

- Annotation definition management (CRUD for AnnotationDefinition — already exists elsewhere)
- Taxonomy definition management (already exists)
- Migrating `market_phase` to the Taxonomy relation
