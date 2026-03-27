## Why

The trading journal UI has three critical issues preventing proper data filtering and display:

1. **Playbooks/tags not visible immediately after creation** - Users create items but don't see them in the UI until they create a second item. This is caused by React Query cache invalidation race conditions that delay the optimistic UI update.
2. **Tag filtering broken in trades overview** - Tag filter controls exist but filtering doesn't work correctly on the backend endpoint. 
3. **Account and playbook filtering missing** - Users cannot filter trades by account or strategy (playbook), and the account filter is incorrectly hidden for single-account users.

These issues significantly impact the user experience when journaling trades and analyzing trading data.

## What Changes

### Frontend (React Query & Components)
- Implement **optimistic updates** in `useCreatePlaybook()` and `useCreateTag()` hooks to immediately show new items in lists without waiting for API response
- Fix **tag filtering** in `TradeFilterBar` component to properly pass tag IDs to backend endpoint
- Make **account filter visible** for all users (remove `accounts.length > 1` condition)
- Add **playbook filter** to trades table with proper data loading and visibility states
- Improve **filter panel loading states** for better UX during data fetching

### Backend (API Endpoint)
- Verify `/api/v1/trades` endpoint correctly filters by `tag_ids` query parameter
- Ensure `account_id` and `playbook_id` filters work as expected
- Add integration tests to validate filter combinations

## Capabilities

### New Capabilities
- `optimistic-updates`: Immediately display newly created playbooks and tags in UI before API confirmation
- `playbook-filter-trades`: Add filtering by playbook/strategy in trades table with proper state management

### Modified Capabilities
- `trades-filtering`: Extend to support account, playbook, and tag filters with proper data loading states and visibility logic

## Impact

**Affected code:**
- Frontend: `/frontend/components/trades/TradeFilterBar.tsx`, `/frontend/components/playbooks/PlaybookList.tsx`, `/frontend/components/tags/TagList.tsx`, `/frontend/hooks/useTrades.ts`, `/frontend/hooks/usePlaybooks.ts`, `/frontend/hooks/useTags.ts`
- Backend: `/app/api/trades.py` (GET endpoint)
- Tests: `/tests/api/test_trades.py`

**User impact:**
- Immediate visual feedback when creating playbooks/tags
- Full filtering capability across all trade attributes
- Consistent filter UI regardless of account count
