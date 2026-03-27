## 1. Optimistic Updates for Playbooks

- [x] 1.1 Modify `useCreatePlaybook()` hook to implement optimistic update logic using `queryClient.setQueryData()`
- [x] 1.2 Add error rollback to `useCreatePlaybook()` to remove optimistically added playbook on API error
- [x] 1.3 Remove form-closing logic from PlaybookForm component (let hook handle state)
- [x] 1.4 Test playbook creation shows immediately without requiring second creation
- [x] 1.5 Test error handling: verify rollback when playbook creation fails

## 2. Optimistic Updates for Tags

- [x] 2.1 Modify `useCreateTag()` hook to implement optimistic update logic using `queryClient.setQueryData()`
- [x] 2.2 Add error rollback to `useCreateTag()` to remove optimistically added tag on API error
- [x] 2.3 Remove form-closing logic from TagForm component
- [x] 2.4 Test tag creation shows immediately without requiring second creation
- [x] 2.5 Test error handling: verify rollback when tag creation fails

## 3. Tag Filtering in Trades Overview

- [x] 3.1 Verify tag filtering URL parameters are correctly built in `TradeFilterBar.tsx` (tag_ids array)
- [x] 3.2 Verify backend `/api/v1/trades` endpoint correctly filters by tag_ids parameter
- [x] 3.3 Add integration test for tag filtering on backend (test at least 2 tags together)
- [x] 3.4 Add loading state indicator for tags section in TradeFilterBar
- [x] 3.5 Test tag filtering end-to-end: create trade with tag, filter by tag, verify result

## 4. Account Filtering Visibility

- [x] 4.1 Remove `accounts.length > 1` condition from account filter visibility in TradeFilterBar.tsx
- [x] 4.2 Ensure account filter shows for all users with 1+ accounts
- [x] 4.3 Add loading state indicator while accounts are loading
- [x] 4.4 Test single-account user sees account filter
- [x] 4.5 Test multi-account user still sees account filter

## 5. Playbook Filtering (New)

- [x] 5.1 Add playbook filter selector component to TradeFilterBar.tsx (single-select dropdown)
- [x] 5.2 Implement conditional visibility: show only when playbooks.length > 0
- [x] 5.3 Add loading state indicator while playbooks are loading
- [x] 5.4 Wire filter to `useTrades()` hook (add playbook_id to filter parameters)
- [x] 5.5 Verify URL parameters include playbook_id when selected
- [x] 5.6 Test playbook filtering end-to-end: create trade with playbook, filter by playbook, verify result

## 6. Combined Filter Testing

- [x] 6.1 Test account + tag filtering together (should show trades matching both)
- [x] 6.2 Test account + playbook filtering together
- [x] 6.3 Test tag + playbook filtering together
- [x] 6.4 Test all three filters combined (account + tag + playbook)
- [x] 6.5 Test clearing individual filters while others remain active

## 7. Verification & Cleanup

- [x] 7.1 Run frontend linting and type checking (TypeScript strict mode)
- [x] 7.2 Verify no console errors or warnings in browser dev tools
- [x] 7.3 Test responsive design: verify filters work on mobile/tablet sizes
- [x] 7.4 Document any API behavior assumptions discovered during testing
- [x] 7.5 Update CHANGELOG.md with changes made
