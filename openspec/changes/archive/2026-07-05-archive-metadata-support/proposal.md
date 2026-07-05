## Why

When managing trading tags (taxonomies) and metrics (annotation definitions), users need both the ability to permanently delete definitions (hard-delete) and the ability to temporarily retire/deactivate them (soft-delete/archived) without breaking historical trade logging and dashboard statistics. This proposal establishes explicit archiving/unarchiving operations and library filtering to give users a fully flexible metadata lifecycle.

## What Changes

- **Explicit Archiving**: Add explicit "Archive" action buttons in the Details View of both tags and metrics. Clicking "Archive" sets `is_archived = True` on the definition.
- **Unarchiving**: Add "Unarchive" action buttons in the Details View when an item is currently archived, allowing users to reactivate it.
- **Library Filtering**: Introduce a "Show Archived" toggle switch in the global Library pages (both Tags and Metrics). By default, it is turned off (hiding archived items). When toggled on, it reveals archived items with a clear "Archived" visual badge.
- **Cascade Hard-Deletion (Danger Zone)**: Document and fully establish cascading hard-deletion which wipes the definition and clears all related intermediate assignment tables when completed via the name-matching Danger Zone.

## Capabilities

### New Capabilities
- `metadata-archiving`: Expose explicit archive/unarchive APIs and add a "Show Archived" toggle in the Library frontend grids to display/hide retired elements.

### Modified Capabilities
- `taxonomy-management`: Modify the taxonomy delete operation to support a `force` query parameter for cascading hard-deletion, alongside standard soft-deletion.
- `annotation-definition-management`: Modify the annotation definition delete operation to support a `force` query parameter for cascading hard-deletion, alongside standard soft-deletion.

## Impact

- **Backend**: API controllers (`taxonomies.py`, `annotation_definitions.py`) and services already support archiving/unarchiving. The database schemas are already equipped with the `is_archived` column.
- **Frontend**: `TaxonomyManager.tsx` and `AnnotationManager.tsx` require updates to add the archive/unarchive triggers, the global list toggle, and the filtered query logic.
