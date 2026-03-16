## 1. Backend Schemas

- [ ] 1.1 Add `BulkTradeRequest` Pydantic schema to `backend/app/schemas/trade.py`: `trade_ids: list[UUID]` with `max_length=500` validator
- [ ] 1.2 Add `BulkAssignTagsRequest` schema: extends `BulkTradeRequest` with `tag_ids: list[UUID]`
- [ ] 1.3 Add `BulkAssignPlaybookRequest` schema: extends `BulkTradeRequest` with `playbook_id: UUID | None`
- [ ] 1.4 Add `BulkOperationResult` response schema: `affected_count: int`
- [ ] 1.5 Add constant `MAX_BULK_SIZE = 500` to `backend/app/core/constants.py`

## 2. Backend Repository

- [ ] 2.1 Add `bulk_delete(user_id, trade_ids)` async method to `TradeRepository` — DELETE WHERE id IN (...) AND user_id = user_id; return row count
- [ ] 2.2 Add `bulk_assign_tags(user_id, trade_ids, tag_ids)` async method to `TradeRepository` — within a transaction: DELETE existing `trade_tags` for matched trades, INSERT new rows for each (trade_id, tag_id) pair
- [ ] 2.3 Add `bulk_assign_playbook(user_id, trade_ids, playbook_id)` async method to `TradeRepository` — UPDATE trades SET playbook_id = ? WHERE id IN (...) AND user_id = user_id; return row count

## 3. Backend Service

- [ ] 3.1 Add `bulk_delete_trades(user_id, trade_ids)` method to `TradeService` delegating to repository; handle empty list early-exit
- [ ] 3.2 Add `bulk_assign_tags(user_id, trade_ids, tag_ids)` method to `TradeService`; validate that all tag_ids belong to user (call TagRepository); raise 404 if any unknown
- [ ] 3.3 Add `bulk_assign_playbook(user_id, trade_ids, playbook_id)` method to `TradeService`; if playbook_id is not None, validate it belongs to user; raise 404 if unknown

## 4. Backend API Routes

- [ ] 4.1 Add `POST /trades/bulk/delete` endpoint to `backend/app/api/v1/trades.py`; body: `BulkTradeRequest`; returns `BulkOperationResult` with HTTP 200
- [ ] 4.2 Add `POST /trades/bulk/assign-tags` endpoint; body: `BulkAssignTagsRequest`; returns `BulkOperationResult`
- [ ] 4.3 Add `POST /trades/bulk/assign-playbook` endpoint; body: `BulkAssignPlaybookRequest`; returns `BulkOperationResult`

## 5. Backend Tests

- [ ] 5.1 Write unit tests for `TradeService.bulk_delete_trades` (mock repo, verify empty list, ownership skip)
- [ ] 5.2 Write unit tests for `TradeService.bulk_assign_tags` (mock repo+tag repo, verify 404 on unknown tag)
- [ ] 5.3 Write unit tests for `TradeService.bulk_assign_playbook` (mock repo+playbook repo, verify null playbook clears, 404 on unknown playbook)
- [ ] 5.4 Write integration tests for `TradeRepository.bulk_delete` (real test DB)
- [ ] 5.5 Write integration tests for `TradeRepository.bulk_assign_tags` (real test DB, verify replacement semantics)
- [ ] 5.6 Write integration tests for `TradeRepository.bulk_assign_playbook` (real test DB)
- [ ] 5.7 Write API tests for all 3 endpoints: 401 unauthenticated, 422 oversized batch, 200 success, foreign ID skip behavior

## 6. OpenAPI Client Sync

- [ ] 6.1 Run `openapi-sync` skill to regenerate the frontend TypeScript API client

## 7. Frontend Verification

- [ ] 7.1 Confirm that the existing bulk hooks (`useBulkDeleteTrades`, `useBulkAssignTags`, `useBulkAssignPlaybook`) in the frontend correctly call the new endpoints (no frontend code changes expected)

## 8. Lint, Types, and Commit

- [ ] 8.1 Run `lint-check` skill — fix all ruff and mypy errors
- [ ] 8.2 Run `unit-test` skill — ensure all tests pass
- [ ] 8.3 Create git commit using `commit-helper` skill
