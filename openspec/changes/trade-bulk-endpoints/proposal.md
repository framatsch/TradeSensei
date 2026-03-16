## Why

The frontend already implements bulk-action UI (select-all checkboxes, `BulkActionToolbar`, bulk hooks) that expects three backend endpoints: bulk delete, bulk assign tags, and bulk assign playbook. These endpoints were referenced in `ui-gap-fixes` but were never actually added to the backend. Any user attempting to use bulk operations in the frontend gets a 404 or connection error.

## What Changes

- New endpoint `POST /trades/bulk/delete` — deletes a list of trades by ID
- New endpoint `POST /trades/bulk/assign-tags` — replaces tags on a list of trades
- New endpoint `POST /trades/bulk/assign-playbook` — sets the playbook on a list of trades
- Request body for all three uses a common `BulkTradeRequest` schema with a `trade_ids: list[UUID]` field plus endpoint-specific fields
- All three endpoints enforce ownership — only trades belonging to the authenticated user are affected

## Capabilities

### New Capabilities

- `trade-bulk-delete`: Bulk delete multiple trades in a single authenticated request
- `trade-bulk-assign-tags`: Bulk replace tags on multiple trades in a single request
- `trade-bulk-assign-playbook`: Bulk set the playbook on multiple trades in a single request

### Modified Capabilities

<!-- none -->

## Impact

- **Backend**: 3 new route handlers in `backend/app/api/v1/trades.py`; new service methods in `TradeService`; new repository methods in `TradeRepository`; new Pydantic schemas in `backend/app/schemas/trade.py`
- **Frontend**: No changes needed — hooks already call these endpoints; they will start working once the backend is in place
- **Database**: No schema changes; operations use existing `trades`, `trade_tags` tables
- **Breaking**: None — additive only
