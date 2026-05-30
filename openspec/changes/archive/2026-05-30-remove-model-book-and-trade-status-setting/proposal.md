## Why

The Model Book feature (star/bookmark on trades and check-ins) is being superseded by a Taxonomy system that will provide richer, more flexible classification. Continuing to maintain two parallel classification systems creates confusion and technical debt. Additionally, users need a UI setting to control whether open trades appear in dashboard/workspace views, since performance metrics are typically based on closed trades and open positions can distort statistics.

## What Changes

- **BREAKING** Remove `is_modelbook` boolean field from Trade and DailyCheckin models (DB migration drops columns)
- **BREAKING** Remove all Model Book API endpoints (`/model-book`, `PATCH /trades/{id}/modelbook`, `PATCH /checkins/{date}/modelbook`)
- Remove all Model Book backend layers: `model_book_repository.py`, `model_book_service.py`, `model_book.py` (schemas), `model_book.py` (api)
- Remove frontend components: `StarButton`, `ModelBookCard`, `components/library/model-book` page, hooks `useTradeModelBook`, `useCheckinModelBook`
- Remove Model Book library route (`/dashboard/library` or model-book sub-route)
- Remove `is_modelbook` from Trade and Checkin response schemas (no longer returned in API responses)
- Add `show_open_trades` boolean UI setting (default: `false`) to user settings
- When `show_open_trades = false`: all dashboard/workspace trade lists show only `status = CLOSED` trades; open/closed filter toggle is hidden
- When `show_open_trades = true`: all trades are shown by default; an Open/Closed/All filter toggle appears in the filter bar
- Add `show_open_trades` to `FeaturesSettings` component (renamed/extended as "UI Settings")
- Update Help page to document the new setting and its effect

## Capabilities

### New Capabilities
- `trade-status-ui-setting`: Per-user setting `show_open_trades` that controls visibility of open trades across all dashboard/workspace views and conditionally renders the status filter toggle

### Modified Capabilities
- `model-book-starring`: **Removed** — `is_modelbook` flag and all related endpoints, services, repositories, schemas, and UI components are deleted
- `checkin-modelbook-filters`: **Removed** — Model Book gallery page and its filter panel are deleted
- `chart-display-settings`: Extended to include the new `show_open_trades` setting in the existing settings infrastructure

## Impact

- **Backend**: `backend/app/api/v1/model_book.py`, `backend/app/services/model_book_service.py`, `backend/app/repositories/model_book_repository.py`, `backend/app/schemas/model_book.py`, `backend/app/models/trade.py`, `backend/app/models/daily_checkin.py`, `backend/app/schemas/trade.py`, `backend/app/schemas/daily_checkin.py`, `backend/app/api/v1/router.py`
- **DB Migration**: Alembic migration to drop `is_modelbook` from `trades` and `daily_checkins` tables
- **Frontend**: `components/shared/StarButton.tsx`, `components/checkin/ModelBookCard.tsx`, `hooks/useTradeModelBook.ts`, `hooks/useCheckinModelBook.ts`, library/model-book route, `app/dashboard/trades/[id]/page.tsx`, `app/dashboard/checkins/[date]/CheckinDateClient.tsx`, `lib/featureFlags.ts`, `components/settings/FeaturesSettings.tsx`, `app/help/HelpClient.tsx`
- **Tests**: Remove model-book related tests; add tests for `show_open_trades` setting and filter toggle visibility
