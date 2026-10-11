## Why

Trading strategies evolve over time: traders frequently pause or retire playbooks that are no longer actively traded. Currently, the primary removal action in the UI table is a hard delete, which detaches the playbook from all historical trades (`playbook_id` is set to null via `ON DELETE SET NULL`), irreversibly destroying strategy attribution in historical reporting and analytics. Having a prominent delete icon on every row in the overview table creates a high risk of accidental data loss when users simply want to archive or deactivate a strategy.

Furthermore, as a trader builds a playbook library with various tags (e.g., Breakout, Mean Reversion, Scalp), finding and reviewing playbooks becomes cumbersome without dedicated filtering and sorting capabilities.

To solve this:
1. Hard deletion is removed from the overview table and confined strictly to the playbook editor/detail view.
2. The table's `Status` column becomes an interactive toggle for "Active / Inactive".
3. A collapsible filter bar (matching the Trading Log / `TradeFilterBar` design) and sortable column headers are added to `PlaybookList`.
4. Inactive playbooks are filtered out of trade assignment dropdowns for new trades.

## What Changes

- **Removal of Row Delete Action**: Remove the delete (trash can) button and inline delete confirmation from `PlaybookList.tsx`. Permanent deletion remains accessible exclusively within the playbook editor (`PlaybookEditorClient.tsx`).
- **Interactive Status Column Toggle**: Transform the `Status` column in `PlaybookList.tsx` into an interactive active/inactive toggle (clickable status badge/switch with optimistic update).
- **Collapsible Playbook Filter Bar**: Introduce an expandable filter bar in `PlaybookList` matching the Trading Log (`TradeFilterBar`) pattern, complete with an open/close toggle button, active filter counter badge, and a "Clear all" button.
- **Filter Controls**:
  - **Status Filter**: Toggle/select between "Active" (default), "Inactive", and "All".
  - **Tag Filter**: Multi-select filter by playbook taxonomy tags.
  - **Search**: Free-text search matching playbook name or description.
- **Table Column Sorting**: Enable interactive column header sorting in `PlaybookList` (sort by Name, Created Date, or Status in ascending/descending order).
- **Playbook Editor Active / Inactive Toggle**: Add an "Active / Inactive" toggle control to the playbook editor header/settings in `PlaybookEditorClient`.
- **Trade Assignment Filtering**: Restrict playbook selection dropdowns in trade metadata (`QualitativeMetadataPanel`) so that inactive playbooks are excluded from selectable options for new assignments, while preserving and visibly labeling any previously assigned inactive playbook on historical trades.

## Capabilities

### New Capabilities
- `playbook-lifecycle-status`: Manage active / inactive state of playbooks across the overview list, editor, and trade attribution selectors, and restrict deletion to the editor.
- `playbook-list-filtering-sorting`: Expandable filter bar (status, tags, search) and table column sorting for the playbook overview table.

### Modified Capabilities
<!-- No requirement changes to existing specs -->

## Impact

- **Frontend Components**:
  - `frontend/components/playbooks/PlaybookFilterBar.tsx`: New collapsible filter component inspired by `TradeFilterBar`.
  - `frontend/components/playbooks/PlaybookList.tsx`: Integrated filter bar, sortable table headers, interactive status toggle, and removal of row delete action.
  - `frontend/components/playbooks/PlaybookEditorClient.tsx`: Add active/inactive toggle switch; retains exclusive permanent delete button.
  - `frontend/components/trades/QualitativeMetadataPanel.tsx`: Filter selectable playbooks to active only, with fallback to display existing assigned inactive playbooks.
- **Frontend Hooks**:
  - `frontend/hooks/usePlaybooks.ts`: Ensure `useUpdatePlaybook` seamlessly supports status toggling with optimistic updates.
- **Backend / APIs**:
  - Backend already provides `is_active` in `PlaybookRead` and `PlaybookUpdate`, and already includes eager-loaded `taxonomies` on playbook queries. No backend API or database schema changes are required.
