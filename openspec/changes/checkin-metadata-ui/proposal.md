# Proposal: checkin-metadata-ui

## Summary

Extend the Check-in Form and Filter Bar to support full Tag (Taxonomy) and Annotation management. Replace the `market_phase` string field with a default `string_enum` AnnotationDefinition called "Market Regime". Additionally extend the Trade and Workspace filter bars with the same generic Annotation Filter mechanism, and close the gaps in the MCP interface so AI agents can list check-ins, read/write annotations on check-ins, and use taxonomy + annotation filters across all entity types.

## Problem

- The Check-in Form has no UI for assigning Tags (Taxonomy via assign/remove endpoints) or for reading/setting Annotation values. The API and DB layer for both already exist.
- `market_phase` is a free-text String field on `daily_checkins` that duplicates what an `AnnotationDefinition(type=string_enum, scope=checkins)` can already do — with less flexibility and no filter support.
- The Check-in Filter Bar cannot filter by taxonomy_ids or annotation values.
- The Trade and Workspace filter bars lack annotation-based filtering.
- The MCP interface has no tools for listing check-ins, filtering check-ins by annotation/taxonomy, syncing check-in metadata, or filtering trades by annotation values via the standard trade endpoints.

## Proposed Solution

### 1. Deprecate `market_phase` → Replace with "Market Regime" Annotation

Add a new default `AnnotationDefinition` to `seed_defaults`:

```python
{
    "name": "Market Regime",
    "type": "string_enum",
    "scope": "checkins",
    "scale_labels": {"options": ["Bull", "Bear", "Chop", "Sideways"]},
    "icon_identifier": "trending-up",
    "description": "Overall market condition for the session",
}
```

The `market_phase` field on `DailyCheckin` is **kept in the DB** (no migration needed for existing data) but:
- The UI removes the dedicated Market Phase section from `CheckinForm`
- The filter removes the `regime` select from `CheckinFilterBar`
- Both are replaced by the generic Annotations UI/filter which renders "Market Regime" automatically
- A manual note in the docs (not committed) instructs existing users to re-enter their market regime values via the new annotation field

### 2. Check-in Form — Tags (Taxonomies)

Add a multi-select Tags field. Uses `POST /{checkin_id}/taxonomies` and `DELETE /{checkin_id}/taxonomies/{id}`. Buffered for new check-ins, applied after initial create.

### 3. Check-in Form — Annotations

Add an Annotations section rendering a typed input per AnnotationDefinition with scope="checkins" or scope="both":

| type | UI element |
|---|---|
| bool | Toggle / Checkbox |
| string_enum | Dropdown (from `scale_labels.options`) |
| int | Number input (integer, optional min/max from scale_labels) |
| float | Number input (decimal, optional min/max from scale_labels) |

Values saved via POST/PUT annotation endpoints. Clear button calls DELETE.

### 4. Check-in Filter — taxonomy_ids + annotation_filters

Extend `CheckinFilterBar` and `GET /api/v1/checkins`:
- `taxonomy_ids`: multi-select (OR across selected tags)
- `annotation_filters`: `[{ annotation_definition_id, operator, value, logic: AND|OR }]`
- Remove `regime` query param (replaced by annotation_filters)

### 5. Generic Annotation Filter — Trades & Workspace

Extract annotation filter helpers from `mcp.py` into `app/repositories/_annotation_filter.py`. Expose via `GET /trades` and Workspace. Add `AnnotationFilterRows` shared frontend component.

### 6. MCP Interface Gaps

Add the following MCP tools:

| Tool | Description |
|---|---|
| `list_checkins` | List check-ins with date range, taxonomy, annotation filters; returns assignments |
| `sync_checkin_metadata` | Bulk assign taxonomy tags and annotation values to check-ins |
| `search_trades_advanced` extended | Add `annotation_filters` to existing tool (currently only taxonomy_ids) |

`get_metadata_schema` already returns all taxonomies and annotation_definitions — no change needed there.

## Operator semantics

| type | allowed operators |
|---|---|
| bool | `eq` |
| string_enum | `eq`, `neq` |
| int | `eq`, `neq`, `gt`, `gte`, `lt`, `lte` |
| float | `eq`, `neq`, `gt`, `gte`, `lt`, `lte` |

Multiple annotation_filters use per-entry `logic: AND|OR` (first entry always AND).

## Out of scope

- Annotation definition management UI (already exists)
- Taxonomy definition management UI (already exists)
- Hard-migrating existing `market_phase` DB values (field stays, UI/filter drops it)
