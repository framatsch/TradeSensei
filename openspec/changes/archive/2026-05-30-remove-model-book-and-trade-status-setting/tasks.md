## 1. Backend — Remove Model Book

- [x] 1.1 Delete `backend/app/api/v1/model_book.py`
- [x] 1.2 Delete `backend/app/services/model_book_service.py`
- [x] 1.3 Delete `backend/app/repositories/model_book_repository.py`
- [x] 1.4 Delete `backend/app/schemas/model_book.py`
- [x] 1.5 Remove `model_book` router registration from `backend/app/api/v1/router.py`
- [x] 1.6 Remove `is_modelbook` field from `backend/app/models/trade.py`
- [x] 1.7 Remove `is_modelbook` field from `backend/app/models/daily_checkin.py`
- [x] 1.8 Remove `is_modelbook` from Trade Pydantic schemas (`backend/app/schemas/trade.py`)
- [x] 1.9 Remove `is_modelbook` from DailyCheckin Pydantic schemas (`backend/app/schemas/daily_checkin.py`)
- [x] 1.10 Remove any `is_modelbook` filtering or sorting logic from `backend/app/repositories/trade_repository.py` and `backend/app/repositories/daily_checkin_repository.py`
- [x] 1.11 Remove any model book references from `backend/app/services/trade_service.py` and `backend/app/services/daily_checkin_service.py`

## 2. Database Migration — Drop is_modelbook Columns

- [x] 2.1 Generate Alembic migration: drop `is_modelbook` column from `trades` table
- [x] 2.2 Add drop of `is_modelbook` column from `daily_checkins` table to the same migration
- [x] 2.3 Apply migration and verify schema with `alembic upgrade head`

## 3. Backend — Add show_open_trades Setting

- [x] 3.1 Add `show_open_trades: bool = False` to `UserSettingsRead` schema in `backend/app/schemas/user.py`
- [x] 3.2 Add `show_open_trades: bool | None = None` to `UserSettingsUpdate` schema
- [x] 3.3 Update user settings service to read/write `show_open_trades` from the `features` JSONB column (no migration needed)
- [x] 3.4 Verify `GET /api/v1/users/me/settings` returns `show_open_trades: false` when not set

## 4. OpenAPI Sync

- [x] 4.1 Run `openapi-sync` skill to regenerate the frontend TypeScript client after all backend changes

## 5. Frontend — Remove Model Book Components

- [x] 5.1 Delete `frontend/components/shared/StarButton.tsx`
- [x] 5.2 Delete `frontend/components/checkin/ModelBookCard.tsx`
- [x] 5.3 Delete `frontend/components/checkin/ModelBookFilterBar.tsx`
- [x] 5.4 Delete `frontend/components/checkin/ModelBookView.tsx`
- [x] 5.5 Delete `frontend/hooks/useTradeModelBook.ts`
- [x] 5.6 Delete `frontend/hooks/useCheckinModelBook.ts`
- [x] 5.7 Delete `frontend/hooks/useModelBookEntries.ts`
- [x] 5.8 Remove `ModelBookView` import and render from `frontend/app/dashboard/layout.tsx`
- [x] 5.9 Remove `StarButton` and model book mutation from `frontend/app/dashboard/trades/[id]/page.tsx`
- [x] 5.10 Remove `StarButton` and model book mutation from `frontend/app/dashboard/checkins/[date]/CheckinDateClient.tsx`
- [x] 5.11 Remove model book references from `frontend/app/dashboard/checkins/CheckinsPageClient.tsx`
- [x] 5.12 Remove `is_modelbook` references from any test files (`__tests__/components/trades/ExecutionLegsTable.test.tsx`, `ExecutionRow.test.tsx`)

## 6. Frontend — Library Route Cleanup

- [x] 6.1 Update `frontend/app/dashboard/library/page.tsx` redirect to point to playbooks (remove any model-book sub-route if it exists)
- [x] 6.2 Verify no broken navigation links to model-book routes remain in nav/sidebar

## 7. Frontend — show_open_trades Setting

- [x] 7.1 Add `show_open_trades` key to `FeatureFlagKey` type and `FEATURE_FLAGS` array in `frontend/lib/featureFlags.ts` with label "Show Open Trades" and description "Show open positions in trade lists and enable the Open/Closed filter."
- [x] 7.2 Update `DEFAULT_SETTINGS` in `frontend/hooks/useSettings.ts` to include `show_open_trades: false`

## 8. Frontend — Trade List Query-Time Override

- [x] 8.1 Create a `useShowOpenTrades()` hook that reads `show_open_trades` from settings
- [x] 8.2 In `frontend/app/dashboard/trades/TradesPageClient.tsx`: when `show_open_trades = false`, force `status=closed` in the API call regardless of URL param
- [x] 8.3 Apply the same override in workspace trade table components (identify all surfaces with trade list API calls)
- [x] 8.4 Apply the same override in dashboard trade widgets
- [x] 8.5 Conditionally hide the Open/Closed/All status filter toggle in the filter bar when `show_open_trades = false`
- [x] 8.6 Add info banner: when `show_open_trades = false` AND URL contains `status=open`, show dismissible banner "Open trades are hidden. Enable 'Show Open Trades' in Settings → UI to show them."

## 9. Frontend — Help Page Update

- [x] 9.1 Add a section in `frontend/app/help/HelpClient.tsx` documenting the "Show Open Trades" setting: what it does, that default is off (only closed trades shown), how to enable it, and that the Open/Closed filter toggle appears when enabled

## 10. Tests — Backend

- [x] 10.1 Delete `backend/tests/test_modelbook_api.py` (entire file, all 229 lines)
- [x] 10.2 Remove `is_modelbook = False` fixture setup from `backend/tests/test_metrics_service.py` (line 72) — update trade factory/fixture to no longer set this field
- [x] 10.3 Remove `is_modelbook = False` fixture setup from `backend/tests/test_trade_service.py` (line 116) — update trade factory/fixture to no longer set this field
- [x] 10.4 Run full backend test suite and fix any remaining failures caused by removed `is_modelbook` references
- [x] 10.5 Add to `backend/tests/api/test_users.py`: test that `GET /api/v1/users/me/settings` returns `show_open_trades: false` by default
- [x] 10.6 Add to `backend/tests/api/test_users.py`: test that `PUT /api/v1/users/me/settings` with `{"features": {"show_open_trades": true}}` persists and returns `show_open_trades: true`
- [x] 10.7 Add to `backend/tests/api/test_users.py`: test that updating `show_open_trades` does not affect other feature flags

## 11. Tests — Frontend

- [x] 11.1 In `frontend/__tests__/components/trades/ExecutionLegsTable.test.tsx`: remove `is_modelbook: false` from mock trade objects (line 62) and fix any resulting test failures
- [x] 11.2 In `frontend/__tests__/components/trades/ExecutionRow.test.tsx`: remove `is_modelbook: false` from mock trade objects (line 49) and fix any resulting test failures
- [x] 11.3 Run full frontend test suite (`npm test`) and fix any remaining failures caused by removed model book components or hooks
- [x] 11.4 Add frontend test: Open/Closed filter toggle is NOT rendered when `show_open_trades = false` (mock settings hook)
- [x] 11.5 Add frontend test: Open/Closed filter toggle IS rendered when `show_open_trades = true`
- [x] 11.6 Add frontend test: info banner appears when `show_open_trades = false` AND the component receives `status=open` in URL params
- [x] 11.7 Add frontend test: API call uses `status=closed` when `show_open_trades = false` regardless of URL `status` param
