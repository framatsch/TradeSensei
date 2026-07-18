# Design

## Context

Two independent-but-related improvements to the import/account experience. Both are small; this doc records the key decisions so implementation stays surgical.

Relevant existing code:
- Clear-trades primitives already exist: `TradeRepository.delete_by_user_account` (`backend/app/repositories/trade_repository.py:759`), `ExecutionRepository.delete_all_for_account` (`backend/app/repositories/execution.py:391`), `BrokerRawTransactionRepository.delete_by_user_account` (`backend/app/repositories/broker_raw_transaction_repository.py:212`). They are only called from `ImportService.fresh_start_import` and the normal import rebuild path today.
- Fresh-start endpoint (file-coupled): `backend/app/api/v1/imports.py:305`.
- Import UI: `frontend/components/imports/ImportForm.tsx`, IBKR "regler" = `frontend/components/imports/DateRangeVisualizer.tsx`.
- Danger Zone: `frontend/components/accounts/AccountDeleteModal.tsx`, wired via `AccountList.tsx`.

## Decision 1: Standalone clear-trades endpoint (no file, wipes everything)

**Endpoint:** `DELETE /api/v1/portfolios/{portfolio_id}/accounts/{account_id}/trades`

Placed under the account resource because the semantics are "reset this account's data", not "import". Returns a small envelope with deletion counts.

- Deletes trades **including manually-edited** ones (`include_manually_edited=True`) — user chose a true fresh start.
- Also clears executions and raw transactions so a subsequent import rebuilds cleanly (mirrors what `fresh_start_import` does before re-import, minus the re-import).
- Single DB transaction; roll back on any error.
- Requires `acknowledged=true` (query param or body flag) — matches the existing fresh-start acknowledgement pattern.
- Ownership enforced via the account lookup; foreign account → 404 (consistent with existing account routes).

**Service:** add `clear_account_trades(account_id, user_id) -> ClearTradesResult` orchestrating the three repository deletes. Reuse existing repository methods; do not add new query logic.

**Why not reuse `fresh_start_import`?** It hard-requires a file and re-imports. Splitting the destructive reset from the import removes the file coupling the user explicitly asked for ("kontext unabhängig ob files importiert werden oder nicht").

**Audit:** manual event `account.trades_cleared` with `{account_id, trades_deleted, executions_deleted}`. No sensitive fields per the audit policy.

### Alternatives considered
- Add a `days=0`/empty-file mode to fresh-start — rejected; overloads a file endpoint with a non-file semantic.
- Soft-delete / restore — rejected; out of scope, action is destructive by design.

## Decision 2: Move Fresh Start into the Edit Account Danger Zone

Remove the red "Fresh Start" block from `ImportForm` (`:513-622`). Add a "Clear all trades" action inside the **account edit modal's** Danger Zone (`BrokerAccountEditModal`), alongside the existing "Delete Account" action — NOT in the account list overview. It calls the new endpoint via the generated client.

- Placement: inside `BrokerAccountEditModal.tsx` Danger Zone, as a sibling section to "Delete Account". Both destructive actions share the same collapsible Danger Zone region so users look in one place for destructive account operations.
- Confirmation: separate type-to-confirm input for each action (clear vs. delete), consistent with the existing acknowledgement pattern.
- After success: invalidate trade/account queries so the UI reflects the emptied account, then close the modal.

**Why the Danger Zone, not import?** The action is account-scoped and file-independent. Grouping it with account deletion is where users look for destructive account operations.

## Decision 3: Generic broker-agnostic import date-range control

Generalize `DateRangeVisualizer` so it is driven by a **broker capability descriptor** rather than `accountType` branches.

Descriptor shape (frontend-only, colocated with the import components):
```ts
type BrokerImportCapability = {
  maxWindowDays: number;          // IBKR: 365, Schwab: 365 (or its real cap)
  syncParam:                       // how the chosen range maps to the sync request
    | { kind: "fromDate" }         // IBKR: absolute from_date=YYYYMMDD
    | { kind: "days" };            // Schwab: days=N
};
```

- A single `<ImportDateRange>` renders the fill bar + YTD/custom toggle for every broker.
- The descriptor supplies `maxWindowDays` (clamp + limit badge) and `syncParam` (how to serialize the chosen range into the sync request).
- `ImportForm`'s current `accountType === "ibkr" ? <DateRangeVisualizer/> : <select days/>` branch (`:426-458`) collapses to `<ImportDateRange capability={capabilityFor(accountType)} .../>`.
- The sync-request assembly (`ImportForm.tsx:338`) reads `syncParam` from the descriptor instead of branching on `accountType`.

**Backend impact:** none. The backend already accepts `from_date` (IBKR) and `days` (Schwab); only the frontend control that produces them is unified. Descriptor values encode the existing per-broker behavior.

**Extensibility:** a new broker adds one descriptor entry (max window + param kind) and gets the full UI with no component changes — satisfies the "generische import UI" requirement.

### Alternatives considered
- Point Schwab at the existing `DateRangeVisualizer` unchanged — rejected; the component still hard-codes IBKR's 365-day/`from_date` semantics, so it would not be truly generic for a third broker.

## Risks / trade-offs

- **Removing the file-based Fresh Start affordance is behavioral-breaking** for anyone relying on the combined "delete + re-import from file in one click". Mitigation: the two steps remain available (clear trades, then normal import); documented in the proposal as BREAKING.
- **Clear-trades is irreversible.** Mitigation: acknowledgement gate + destructive styling + audit event.
- **Descriptor abstraction is thin by design** — only `maxWindowDays` + `syncParam`. Keeping it minimal avoids speculative configurability (per engineering rules); it can grow if a real third broker needs more.

## Migration

- No DB schema change; no Alembic migration. All deletes use existing repository methods.
- OpenAPI client regenerated to expose the new endpoint (openapi-sync).
