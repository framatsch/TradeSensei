## Context

The `playbooks` table in the database and the SQLAlchemy model ([`Playbook`](file:///home/scheffold/work/TradeSensei/backend/app/models/playbook.py)) already include an `is_active: bool` column defaulting to `true`, and playbooks return their eager-loaded `taxonomies` list. Furthermore, the backend endpoint `PATCH /api/v1/playbooks/{id}` and Pydantic schema [`PlaybookUpdate`](file:///home/scheffold/work/TradeSensei/backend/app/schemas/playbook.py) already support updating `is_active`.

Currently:
1. The overview table has a permanent delete (trash can) button on every row. Deleting a playbook sets `trades.playbook_id = null` for all historical trades (`ON DELETE SET NULL`), creating a severe risk of accidental data loss when users intended merely to retire/hide a strategy.
2. The frontend lacks active/inactive controls.
3. The table has no filtering for status, tags, or search keywords, nor does it support column sorting.

## Goals / Non-Goals

**Goals:**
- Remove the destructive "Delete" action from the table rows in [`PlaybookList.tsx`](file:///home/scheffold/work/TradeSensei/frontend/components/playbooks/PlaybookList.tsx) to prevent accidental historical trade disconnection.
- Retain the permanent "Delete" action exclusively inside [`PlaybookEditorClient.tsx`](file:///home/scheffold/work/TradeSensei/frontend/components/playbooks/PlaybookEditorClient.tsx).
- Transform the `Status` column in `PlaybookList.tsx` into an interactive active/inactive toggle control with instant optimistic updates.
- Keep the table's right action column focused cleanly on the `Edit` button.
- Introduce a collapsible `PlaybookFilterBar` component modeled after `TradeFilterBar` with:
  - Toggle button with chevron and active filter counter badge.
  - Status filter ("Active", "Inactive", "All").
  - Taxonomy tag filter (multi-selection).
  - Search input for playbook name/description.
  - "Clear all" action.
- Implement column-header sorting on `PlaybookList` (Name, Created, Status).
- Provide an "Active / Inactive" toggle control in the editor header/settings in `PlaybookEditorClient.tsx`.
- Ensure trade attribution dropdowns ([`QualitativeMetadataPanel.tsx`](file:///home/scheffold/work/TradeSensei/frontend/components/trades/QualitativeMetadataPanel.tsx)) filter out inactive playbooks for new selections, while preserving and annotating existing inactive assignments as `(Inactive)`.

**Non-Goals:**
- Completely removing the `DELETE /api/v1/playbooks/{id}` endpoint: it remains legitimate for deleting newly created/empty playbooks, but is guarded in the editor.
- Server-side filtering or database schema changes, as client-side filtering over the user's playbook set is fast, reactive, and avoids network overhead.

## Decisions

### 1. Removing Row Delete from Overview Table
- **Decision**: Remove the trash can icon and inline `Delete? Yes/No` popover from `PlaybookList.tsx`. The action column displays only the `Edit` button.
- **Rationale**: Prevents accidental data destruction. When users no longer use a playbook, the correct action is marking it "Inactive". Permanent deletion is reserved for deliberate use inside the editor.

### 2. Interactive Status Column Toggle
- **Decision**: In `PlaybookList.tsx`, render the status in the `Status` column as an interactive badge or pill button that triggers `updatePlaybook({ id: pb.id, payload: { is_active: !pb.is_active } })`.
- **UX Details**:
  - `onClick={(e) => { e.stopPropagation(); toggleStatus(pb); }}` so clicking the status does not trigger the table row's navigation click.
  - Hover effect with title tooltip: e.g. "Click to deactivate" when active, "Click to activate" when inactive.
  - Visual styling: Green pill when active (`bg-success/10 text-success border border-success/30`), neutral pill when inactive (`bg-secondary text-muted-foreground border border-border`).

### 3. Collapsible PlaybookFilterBar Component
- **Decision**: Create a dedicated component `PlaybookFilterBar` styled identically to `TradeFilterBar` (`solid-card shadow-sm mb-4`).
- **Rationale**: Reuses familiar UI patterns across the app (header toggle row with Chevron, counter badge, collapsible content grid).

### 4. Client-Side Filtering & Sorting Pipeline
- **Decision**: Manage filter state (`status: "active" | "inactive" | "all"`, `selectedTagIds: string[]`, `searchQuery: string`) and sort state (`sortKey: "name" | "created_at" | "is_active"`, `sortDirection: "asc" | "desc"`) in `PlaybookList.tsx`.
- **Implementation**:
  ```typescript
  const filteredAndSorted = useMemo(() => {
    return (playbooks ?? [])
      .filter((pb) => {
        // Status filter
        if (filterStatus === "active" && !pb.is_active) return false;
        if (filterStatus === "inactive" && pb.is_active) return false;
        // Search filter
        if (searchQuery) {
          const q = searchQuery.toLowerCase();
          const matchName = pb.name.toLowerCase().includes(q);
          const matchDesc = pb.description?.toLowerCase().includes(q);
          if (!matchName && !matchDesc) return false;
        }
        // Tag filter
        if (selectedTagIds.length > 0) {
          const hasTag = pb.taxonomies?.some((t) => selectedTagIds.includes(t.id));
          if (!hasTag) return false;
        }
        return true;
      })
      .sort((a, b) => {
        // Sort comparator based on sortKey and sortDirection
      });
  }, [playbooks, filterStatus, searchQuery, selectedTagIds, sortKey, sortDirection]);
  ```
- **Rationale**: Instantaneous user feedback, no API latency, zero backend overhead.

### 5. Sortable Table Headers
- **Decision**: Convert table `<th>` elements in `PlaybookList.tsx` into clickable headers with sort direction indicators (`ArrowUpDown`, `ArrowUp`, `ArrowDown`).
- **Rationale**: Standard table interaction pattern.

### 6. Trade Selection Filter with Preservation Fallback
- **Decision**: In `QualitativeMetadataPanel.tsx`:
  ```typescript
  const selectablePlaybooks = useMemo(() => {
    return playbooks.filter((pb) => pb.is_active || pb.id === draftPlaybookId);
  }, [playbooks, draftPlaybookId]);
  ```
  And render:
  ```tsx
  <option key={pb.id} value={pb.id}>
    {pb.name}{!pb.is_active ? " (Inactive)" : ""}
  </option>
  ```
- **Rationale**: Prevents users from assigning retired playbooks to new trades, while ensuring that opening an older trade that has a retired playbook does not silently wipe or invalidate the existing selection.

## Risks / Trade-offs

- **[Risk]** Row click vs. Status button click propagation.  
  → **Mitigation**: Use `e.stopPropagation()` on the status toggle click handler so clicking the status does not navigate to the playbook detail page.
- **[Risk]** Users looking for Delete in the list table.  
  → **Mitigation**: The Edit button opens the editor where the Delete button is clearly located, and deactivating the playbook serves the primary goal of removing it from daily view.
