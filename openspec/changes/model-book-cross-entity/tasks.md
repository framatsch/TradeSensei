## 1. Database Migration

- [x] 1.1 Create Alembic migration adding `is_modelbook` boolean column (default `false`) to `trades` table
- [x] 1.2 Create Alembic migration adding `is_modelbook` boolean column (default `false`) to `daily_checkins` table
- [x] 1.3 Apply migration and verify both columns exist

## 2. Backend — Models & Schemas

- [x] 2.1 Add `is_modelbook: Mapped[bool]` field to `Trade` SQLAlchemy model
- [x] 2.2 Add `is_modelbook: Mapped[bool]` field to `DailyCheckin` SQLAlchemy model
- [x] 2.3 Add `is_modelbook` field to `TradeResponse` and `TradeUpdate` Pydantic schemas
- [x] 2.4 Add `is_modelbook` field to `DailyCheckinResponse` and `DailyCheckinUpdate` Pydantic schemas
- [x] 2.5 Create `ModelBookEntryResponse` discriminated union Pydantic schema (trade + checkin variants)
- [x] 2.6 Create `ModelBookEntriesPage` paginated response schema

## 3. Backend — Star Toggle Endpoints

- [x] 3.1 Add `PATCH /trades/{trade_id}/modelbook` endpoint in trade router
- [x] 3.2 Add `PATCH /checkins/{date}/modelbook` endpoint in checkin router
- [x] 3.3 Add `update_modelbook_flag` method to `TradeRepository`
- [x] 3.4 Add `update_modelbook_flag` method to `CheckinRepository`

## 4. Backend — Aggregation Endpoint

- [x] 4.1 Create `GET /model-book/entries` endpoint in a new `model_book` router
- [x] 4.2 Implement `ModelBookRepository.get_entries()` with `UNION ALL` query joining starred trades and check-ins, sorted by date desc
- [x] 4.3 Add query parameters: `entity_type` (trade | checkin | all), `from_date`, `to_date`, `page`, `per_page`
- [x] 4.4 Register `model_book` router in `app/api/v1/__init__.py`

## 5. API Client Regeneration

- [x] 5.1 Run `openapi-sync` to regenerate the frontend TypeScript API client

## 6. Frontend — Star Toggle Components

- [x] 6.1 Create `StarButton` reusable component (filled/outline star icon, loading state, onClick handler)
- [x] 6.2 Add `StarButton` to Trade Detail page toolbar (reads `trade.is_modelbook`, calls PATCH on click)
- [x] 6.3 Add `StarButton` to Check-in form toolbar (reads `checkin.is_modelbook`, calls PATCH on click)
- [x] 6.4 Add `useTradeModelBook` hook wrapping the PATCH trade modelbook API call with optimistic update
- [x] 6.5 Add `useCheckinModelBook` hook wrapping the PATCH checkin modelbook API call

## 7. Frontend — Model Book Gallery

- [x] 7.1 Create `ModelBookCard` component with trade variant (symbol, R-multiple, tags, image preview, type label)
- [x] 7.2 Create `ModelBookCard` check-in variant (date, market phase pill, screenshot preview, type label)
- [x] 7.3 Replace `ModelBookView.tsx` with new cross-entity implementation using `GET /model-book/entries`
- [x] 7.4 Add `useModelBookEntries` hook wrapping the aggregation endpoint
- [x] 7.5 Wire pagination controls (previous/next) into the new `ModelBookView`
- [x] 7.6 Implement empty state with CTA explaining how to star items

## 8. Frontend — Filter Bar

- [x] 8.1 Add entity type toggle (All / Trades / Check-ins) to `ModelBookFilterBar`
- [x] 8.2 Hide regime filter when entity type is "Trades"
- [x] 8.3 Pass `entity_type` to the `useModelBookEntries` hook
- [x] 8.4 Persist entity type selection in URL params (via `useCheckinParams` or equivalent)

## 9. Mockup

```text
+---------------------------------------------------------------------------------+
| [Timeline] [Gallery] [MODEL BOOK]                        [+ Today's Check-in]  |
+---------------------------------------------------------------------------------+
| [ All ▾ | Trades | Check-ins ]  [ Date Range ▾ ]  [ Regime ▾ ]   [ Clear All ] |
+---------------------------------------------------------------------------------+
|                                                                                 |
|  +--------------------------+  +--------------------------+  +--------------+  |
|  | TRADE           [★]      |  | CHECK-IN        [★]      |  | TRADE  [★]   |  |
|  | MSFT — Breakout          |  | May 10 — Bullish         |  | AAPL—Reversal|  |
|  |--------------------------|  |--------------------------|  |--------------|  |
|  | [ Image Preview ]        |  | [ Screenshot Preview ]   |  | [No Image]   |  |
|  |                          |  |                          |  |              |  |
|  | Result: +2.4 R           |  | Volatility: Low          |  | Result: +1.8R|  |
|  | Tags: [A+] [Earnings]    |  | Tags: [Gap Up]           |  | [VWAP Bounce]|  |
|  +--------------------------+  +--------------------------+  +--------------+  |
|                                                                                 |
|  < Prev   Page 1 of 4   Next >                                                  |
+---------------------------------------------------------------------------------+
```
