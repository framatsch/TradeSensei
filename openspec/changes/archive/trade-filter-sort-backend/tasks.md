## 1. Backend Schemas

- [ ] 1.1 Add `TradeFilterParams` Pydantic model to `backend/app/schemas/trade.py`: `symbol: str | None`, `asset_class: str | None`, `side: str | None`, `account_id: UUID | None`, `playbook_id: UUID | None`, `tag_id: UUID | None`, `from_date: date | None`, `to_date: date | None`, `min_pnl: Decimal | None`, `max_pnl: Decimal | None`
- [ ] 1.2 Add `TradeSortParams` Pydantic model: `sort_by: TradeSortField = TradeSortField.closed_at` (enum: `closed_at`, `symbol`, `pnl`, `pnl_eur`, `asset_class`, `side`), `sort_dir: SortDirection = SortDirection.desc` (enum: `asc`, `desc`)
- [ ] 1.3 Add `TradeSortField` and `SortDirection` enums to `backend/app/schemas/trade.py`

## 2. Database Migration

- [ ] 2.1 Create Alembic migration `0007_trade_filter_indexes.py` adding composite indexes: `ix_trades_user_id_symbol` on `(user_id, symbol)` and `ix_trades_user_id_asset_class` on `(user_id, asset_class)`
- [ ] 2.2 Apply migration locally and verify with `alembic upgrade head`

## 3. Backend Repository

- [ ] 3.1 Update `TradeRepository.list_cursor` signature to accept `filters: TradeFilterParams | None` and `sort: TradeSortParams | None`
- [ ] 3.2 Implement conditional WHERE clause building: for each non-None filter field, append the corresponding SQLAlchemy condition
- [ ] 3.3 Implement tag filter via JOIN to `trade_tags` table when `tag_id` is set
- [ ] 3.4 Implement ORDER BY based on `sort.sort_by` and `sort.sort_dir`
- [ ] 3.5 Implement offset pagination fallback: when `sort_by != closed_at`, accept `skip: int` param and use `.offset(skip)` instead of cursor WHERE clause

## 4. Backend Service

- [ ] 4.1 Update `TradeService.list_trades` signature to pass `filters` and `sort` through to repository

## 5. Backend API Route

- [ ] 5.1 Update `GET /trades` route handler to inject `TradeFilterParams` via `Depends` and `TradeSortParams` via `Depends`
- [ ] 5.2 Add `skip: int = Query(0, ge=0)` parameter for offset pagination fallback
- [ ] 5.3 Pass filter/sort/skip params to service

## 6. Backend Tests

- [ ] 6.1 Write unit tests for `TradeFilterParams` and `TradeSortParams` validation (422 on invalid sort_by)
- [ ] 6.2 Write integration tests for `TradeRepository.list_cursor` with filters: symbol, date range, tag_id, combined AND
- [ ] 6.3 Write integration tests for sort: pnl ascending, symbol ascending, default closed_at descending
- [ ] 6.4 Write API tests for `GET /trades` with filter params (200 correct results), invalid sort_by (422)

## 7. OpenAPI Client Sync

- [ ] 7.1 Run `openapi-sync` skill to regenerate the frontend TypeScript API client

## 8. Frontend Hook Update

- [ ] 8.1 Update `useTrades` hook in `frontend/hooks/useTrades.ts` to accept and pass filter/sort state params to the generated API client method
- [ ] 8.2 Update `TradeFilterBar` component to call the hook's filter state setters (connecting existing UI state to API params instead of client-side filtering)
- [ ] 8.3 Add sort direction toggle control to `TradeTable` column headers if not already present

## 9. Lint, Types, and Commit

- [ ] 9.1 Run `lint-check` skill — fix all ruff and mypy errors
- [ ] 9.2 Run `unit-test` skill — ensure all tests pass
- [ ] 9.3 Create git commit using `commit-helper` skill
