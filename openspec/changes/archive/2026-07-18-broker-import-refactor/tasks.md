## 1. Backend — Clear-Trades Endpoint

- [x] 1.1 Add `ClearTradesResult` schema (`trades_deleted: int`, `executions_deleted: int`) in `backend/app/schemas/`
- [x] 1.2 Add `clear_account_trades(account_id, user_id)` to the account (or trade) service, orchestrating `TradeRepository.delete_by_user_account(include_manually_edited=True)`, `ExecutionRepository.delete_all_for_account`, and `BrokerRawTransactionRepository.delete_by_user_account` in a single transaction; return counts
- [x] 1.3 Add `DELETE /api/v1/portfolios/{portfolio_id}/accounts/{account_id}/trades` route with `acknowledged` flag (400 when false), ownership check (404 on foreign account), returning `ResponseEnvelope[ClearTradesResult]`
- [x] 1.4 Emit manual audit event `account.trades_cleared` with `{account_id, trades_deleted, executions_deleted}` only (no sensitive fields)
- [x] 1.5 Add OpenAPI annotations (summary, description marking it destructive, response model, 400/401/404 responses)

## 2. Backend — Retire File-Coupled Fresh Start (behavioral)

- [x] 2.1 Confirm no remaining caller depends on `POST /imports/{account_id}/fresh-start` for the "reset only" case; keep the endpoint if still used for reset-and-reimport, otherwise deprecate per proposal
- [x] 2.2 Ensure the normal import flow still rebuilds cleanly against an emptied account (no code change expected — verify)

## 3. Frontend — Danger Zone Clear-Trades

- [x] 3.1 Regenerate the OpenAPI client (openapi-sync) so the clear-trades endpoint is available
- [x] 3.2 Add a "Clear all trades" destructive action inside the account edit modal's Danger Zone (`BrokerAccountEditModal`), alongside "Delete Account", with a separate type-to-confirm gate consistent with account deletion
- [x] 3.3 Wire the action to the generated client; on success invalidate trade/account queries and surface a confirmation toast
- [x] 3.4 Remove the file-coupled "Fresh Start" block from `frontend/components/imports/ImportForm.tsx` (`:513-622`)

## 4. Frontend — Generic Import Date-Range Control

- [x] 4.1 Define a `BrokerImportCapability` descriptor (`maxWindowDays`, `syncParam: {kind:"fromDate"|"days"}`) and a `capabilityFor(accountType)` map colocated with the import components
- [x] 4.2 Generalize `DateRangeVisualizer` into `ImportDateRange` driven by the descriptor (clamp to `maxWindowDays`, render fill bar + YTD/custom toggle for all brokers)
- [x] 4.3 Replace the `accountType === "ibkr" ? <DateRangeVisualizer/> : <select days/>` branch in `ImportForm.tsx` (`:426-458`) with `<ImportDateRange capability={...} />`
- [x] 4.4 Replace the sync-request param branching (`ImportForm.tsx:338`) with logic driven by `capability.syncParam` (IBKR `from_date`, Schwab `days`)
- [x] 4.5 Verify Schwab now renders the unified control and still produces a correct `days` sync request; verify IBKR unchanged behavior (365-day cap, `from_date`)

## 5. Tests

- [x] 5.1 Backend: clear-trades deletes trades/executions/raw txns incl. manually-edited; account row survives; 400 without acknowledgement; 404 for foreign account; rollback on failure; audit event emitted with safe metadata
- [x] 5.2 Frontend: Danger Zone clear-trades confirmation + success flow; `ImportDateRange` clamps per descriptor and emits the correct sync param for IBKR (`from_date`) and Schwab (`days`)

## 6. Docs & Changelog

- [x] 6.1 Update `docs/api-usage.md` with the clear-trades endpoint and the unified import UI note
- [x] 6.2 Update AGENTS.md iteration status if applicable
- [x] 6.3 Append to CHANGELOG `[Unreleased]` (Added: clear-trades action, generic import UI; Changed/Removed: file-coupled Fresh Start affordance)
