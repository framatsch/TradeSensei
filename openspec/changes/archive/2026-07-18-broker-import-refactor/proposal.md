## Why

Two rough edges in the import/account experience:

1. **Fresh Start is trapped inside the import flow.** Today the only way to wipe all trades for an account (without deleting the account) is `POST /imports/{account_id}/fresh-start`, which *requires* an uploaded broker file and re-imports in the same step (`backend/app/api/v1/imports.py:305`). The repository primitive to clear trades already exists (`TradeRepository.delete_by_user_account`) but is never exposed as a standalone action. Users who just want a clean slate for an account must either upload a file they may not have, or delete and recreate the whole account.

2. **The import UI is broker-specific and inconsistent.** IBKR renders a rich date-range "regler" (`DateRangeVisualizer`, a fill-bar + YTD/custom toggle capped at 365 days), while Schwab falls back to a plain `Last N days` dropdown (`ImportForm.tsx:426`). The branching is hard-coded per broker type, so adding a third broker means another `if accountType === ...` branch.

## What Changes

- **Backend — standalone "Clear all trades" action.** Add `DELETE /api/v1/portfolios/{portfolio_id}/accounts/{account_id}/trades` that deletes ALL trades, executions, and raw transactions for the account — **without** deleting the account and **without** requiring a file upload. It wipes everything including manually-edited trades (a true fresh start). Requires an explicit `acknowledged=true` confirmation. Emits a manual audit event (`account.trades_cleared`) with safe counts only.
- **Frontend — move Fresh Start into the account Danger Zone.** Add a "Clear all trades" action to the account Danger Zone (`AccountDeleteModal` region), gated by a type-to-confirm / acknowledgement affordance consistent with account deletion. Remove the file-coupled "Fresh Start" block from `ImportForm`; it is now context-independent of whether files are imported.
- **Frontend — generic, broker-agnostic import date-range UI.** Refactor `DateRangeVisualizer` into a broker-capability–driven date-range control. Both IBKR and Schwab render the same control (fill bar + YTD/custom toggle). Broker differences (max window in days, the sync parameter name/shape) are supplied via a small per-broker capability descriptor rather than `if accountType` branching, so future brokers plug in by adding a descriptor entry.
- **BREAKING (behavioral):** The `POST /imports/{account_id}/fresh-start` file-coupled endpoint is superseded by the standalone clear-trades action for the "just reset" use case. The re-import-from-file path remains available via the normal import flow; the dedicated destructive "fresh-start-with-file" affordance is removed from the UI.

## Non-goals

- No change to the actual broker file parsers (IBKR XML, Schwab JSON) or the sync mechanics.
- No new "undo" / soft-delete for cleared trades — the action is destructive by design.
- No backend change to the Schwab sync date-range semantics; only the frontend control that produces the date/days parameter is unified.

## Capabilities

### Modified Capabilities
- `trade-import`: Adds a standalone, file-independent "clear all trades for an account" capability and a generic broker-agnostic import date-range control; supersedes the file-coupled Fresh Start affordance.
- `account-management`: The account Danger Zone gains a non-account-deleting "Clear all trades" destructive action.

## Impact

- **New backend endpoint:** `DELETE /api/v1/portfolios/{portfolio_id}/accounts/{account_id}/trades` in `backend/app/api/v1/accounts.py` (or `trades.py`), wrapping `TradeRepository.delete_by_user_account(include_manually_edited=True)` + `ExecutionRepository.delete_all_for_account` + `BrokerRawTransactionRepository.delete_by_user_account`, in one transaction.
- **Service layer:** New `AccountService.clear_account_trades` (or `TradeService.clear_account_trades`) orchestrating the three repository deletes and returning counts. Reuses existing primitives (`trade_repository.py:759`, `execution.py:391`, `broker_raw_transaction_repository.py:212`).
- **Audit logging:** Manual audit event `account.trades_cleared` with `{account_id, trades_deleted, executions_deleted}` — no P&L, prices, quantities, or notes.
- **Frontend — Danger Zone:** `frontend/components/accounts/AccountDeleteModal.tsx` (or a sibling) gains the "Clear all trades" action; wired via `AccountList.tsx`. Uses the OpenAPI-generated client.
- **Frontend — import UI:** `frontend/components/imports/DateRangeVisualizer.tsx` generalized; `ImportForm.tsx` broker branching (`:426-458`, `:513-622`) replaced by a capability descriptor; the file-based Fresh Start block removed.
- **OpenAPI client:** Regenerated to expose the new clear-trades endpoint (openapi-sync).
- **Docs:** api-usage + dev-guide note the new clear-trades action and the unified import UI.
