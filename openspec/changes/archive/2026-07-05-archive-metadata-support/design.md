## Context

Currently, the backend supports both archiving (setting `is_archived = True`) and hard-deleting of taxonomies (tags) and annotation definitions (metrics). To provide users with a complete and intuitive lifecycle, we need to expose archiving/unarchiving explicitly in the UI and allow filtering retired elements in the global Library pages.

## Goals / Non-Goals

**Goals:**
- Provide explicit "Archive" and "Unarchive" buttons in the Details View of tags and metrics.
- Implement a "Show Archived" toggle filter on global Library grids to hide archived elements by default and allow reactivating them.
- Clean up any ghost references in the Trade Log and Daily Check-ins by excluding archived definitions from serialization.
- Secure hard-deletions using a frontend-enforced Danger Zone requiring exact name-typing confirmation.

**Non-Goals:**
- Adding database schema columns (the existing `is_archived` database fields are completely sufficient).
- Permitting newly archived tags/metrics to be selected inside trade or check-in editor forms.

## Decisions

### Decision 1: Query parameter `force: bool = False` for API Deletion
- **Rationale**: Keeps the standard DELETE endpoints backward-compatible for existing tests (which expect soft-delete/archive when assignments exist). When `force=True` is supplied, it performs the cascade hard-delete.

### Decision 2: Distinct GET `/assignments/count` endpoints
- **Rationale**: Allows the frontend to check whether a definition has active assignments. Based on this, the UI can dynamically switch between a simple delete confirmation box (0 assignments) and a red Danger Zone typing validation box (>0 assignments).

### Decision 3: Frontend "Show Archived" Filter State
- **Rationale**: Keeps retired metadata out of the user's view by default, keeping lists clean, while offering a toggle to inspect and reactivate archived definitions via an "Unarchive" action.

## Risks / Trade-offs

- **[Risk]**: Accidental cascade hard-deletion of tags/metrics destroys historical trade logs.
  - **[Mitigation]**: The frontend Danger Zone locks the delete button behind typing validation matching the exact tag/metric name, ensuring complete user awareness.
