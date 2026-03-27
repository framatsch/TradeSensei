## Context

The frontend uses React Query for server state management with configurable stale times. When users create playbooks or tags, the mutation invalidates the cache, triggering a re-fetch. However, this happens asynchronously while the form component may already be unmounting or the UI hasn't optimistically updated.

The trades table filtering system passes URL parameters to the backend API, but:
1. Tag filtering exists in the filter bar but may not properly persist or apply filters
2. Account filter is conditionally hidden for single-account users (UX issue)
3. Playbook filter UI is missing from the trades table entirely

The backend `/api/v1/trades` endpoint supports these filter parameters, but the frontend isn't fully utilizing them.

## Goals / Non-Goals

**Goals:**
1. Immediately display newly created playbooks and tags in their respective list components using optimistic updates
2. Enable tag filtering in the trades overview with visible, working controls
3. Add account filtering visible to all users (not just multi-account setups)
4. Add playbook/strategy filtering to the trades table
5. Provide proper loading states while filter data loads
6. Maintain React Query cache consistency across all filtering operations

**Non-Goals:**
- Backend API changes (assume existing endpoints work correctly)
- Redesigning filter UI/layout
- Adding new filter types beyond what's currently in specs
- Migration of existing trade data

## Decisions

### Decision 1: Optimistic Updates for Playbooks/Tags
**Choice:** Use React Query's `setQueryData()` in mutation success callbacks to optimistically add new items before API response.

**Why:** 
- Immediate visual feedback without waiting for API round-trip
- Prevents race condition where form closes before data appears
- User sees their creation succeed immediately (best UX)

**Alternative considered:** Keep invalidation approach but delay form close until re-fetch completes (would still feel slow)

**Implementation:**
- In `useCreatePlaybook()`: After successful mutation, call `queryClient.setQueryData(['playbooks'], (old) => [...old, newPlaybook])`
- Same pattern for `useCreateTag()`
- Remove the form close logic from component level; only clear form fields on success

### Decision 2: Unified Filter Architecture
**Choice:** Standardize all filters (tag, account, playbook) to use the same URLSearchParams approach already working for other filters.

**Why:**
- Consistency with existing direction/status/asset_class filters
- Backend already supports all three as query parameters
- No new API changes needed

**Implementation:**
- Tag filtering: Keep existing toggle logic but verify query params are built correctly
- Account filtering: Remove `accounts.length > 1` visibility condition; show for all users
- Playbook filtering: Add dropdown selector (similar to account filter) in TradeFilterBar

### Decision 3: Loading States for Filter Data
**Choice:** Add isLoading indicators in the filter dropdowns (account, playbook) and tag section while data is loading.

**Why:**
- Prevents confusing empty UI during initial data load
- Gives users clear feedback that the app is working
- Better handles race conditions during initial render

**Implementation:**
- `useAccounts()`, `usePlaybooks()`, `useTags()` all return loading state
- TradeFilterBar conditionally renders spinners or skeleton loaders in filter sections
- Show "Loading accounts..." instead of empty dropdown

### Decision 4: Playbook Filter Visibility
**Choice:** Show playbook filter only when playbooks exist (similar to tag filter today).

**Why:**
- Prevents confusing users with empty filter options
- Playbooks are optional; not all users have them
- Aligns with user's mental model of filtering

**Implementation:**
- Add conditional: `{playbooks && playbooks.length > 0 && <PlaybookFilterSelect />}`

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| Optimistic updates could show stale data if API rejects | Add error handling to rollback optimistic state on mutation error |
| Multiple filters applied simultaneously could be slow on backend | Backend already handles filter combinations; performance assumed acceptable |
| Tag filter may have underlying API issue not caught by frontend | Include backend validation test in task list to verify filtering works |
| Adding playbook filter increases filter bar complexity | Keep UI clean by showing only when playbooks exist |
| Users with no accounts/playbooks will see empty filters | Expected behavior; clear messaging needed (done via loading states) |

## Migration Plan

1. **Phase 1:** Deploy optimistic updates for playbooks/tags (low risk, isolated to hooks)
2. **Phase 2:** Deploy filter visibility/loading state changes (UI-only, no API impact)
3. **Phase 3:** Deploy playbook filter addition and tag filter debugging (testing required)
4. **Rollback:** All changes are frontend-only; revert code commits to rollback instantly

No data migration needed.

## Open Questions

- [ ] Has the tag filtering backend endpoint been tested with multiple tag IDs? (Should verify with integration test)
- [ ] Should playbook filter support multi-select like tags, or single-select? (Current design assumes single-select for simplicity)
- [ ] Are there performance concerns with large numbers of playbooks/tags in dropdown? (Assume not; address if testing reveals issues)
