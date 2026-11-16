## Why

Every broker already funnels into `ImportService.import_trades()`, but broker-specific knowledge still leaks into the shared pipeline: Schwab account selection runs inside `import_trades`, a self-heal trigger is hard-wired to `broker == SCHWAB`, combo grouping and position-flip detection read IBKR-only keys (`brokerageOrderID`, `netCash`, `openCloseIndicator`) out of `raw_data`, and sync/auth dispatch is an `if/elif` on `AccountType`. Each new broker (generic file format, Tastytrade, …) would have to touch the core pipeline again — exactly the class of change that has historically introduced import bugs. This change makes the pipeline provably broker-agnostic **without changing any observable import behavior**, as the foundation for `generic-execution-import`.

## What Changes

- Introduce a **broker adapter registry**: each broker is one adapter keyed by its broker key (`ibkr`, `schwab`) that declares capabilities — file import, remote sync, authentication/connection, account binding — plus an import policy.
- Introduce a **canonical import batch** (executions + corporate actions + warnings) as the only thing `ImportService` consumes. Executions remain `BrokerRawTransactionCreate` — no third intermediate format.
- Promote three IBKR-only `raw_data` keys to explicit, broker-neutral columns on `broker_raw_transactions`: `order_id`, `net_cash`, `is_mixed_execution`. Alembic migration backfills existing rows from `raw_data`. Combo building and logical-execution creation read the columns, not `raw_data`.
- Move Schwab account selection + `account_number` binding out of `import_trades` into the Schwab adapter's account-binding capability.
- Replace the `broker == SCHWAB` guard on the pending-protected-close self-heal with an adapter policy flag (enabled for Schwab only — identical behavior).
- Parser warnings are returned in the batch instead of read from mutable parser state via `getattr(parser, "warnings")`.
- Remove the unreachable legacy `parse()` fallback in `import_trades` and the never-overridden `enrich_pnl_eur` hook.
- `BrokerService.sync_account`, connection tests and Schwab OAuth operations dispatch through the adapter registry; `FlexImportService` becomes the IBKR adapter's remote-sync implementation.
- API route handlers derive allowed file extensions and account-type→broker mapping from the registry instead of local constant tables.
- **No** change to API paths, request/response schemas, raw transaction IDs, or import results. No frontend change.

## Capabilities

### New Capabilities
- `broker-adapter-contract`: Contract every broker integration implements (registry, capabilities, canonical batch, policy flags) and the guarantee that the import pipeline contains no broker-specific branching.

### Modified Capabilities
- `raw-transaction-layer`: Raw transactions gain explicit broker-neutral `order_id`, `net_cash` and `is_mixed_execution` fields populated by adapters and backfilled for existing rows.

## Impact

- Backend: `app/services/import_service.py`, `app/services/broker_service.py`, `app/services/flex_import_service.py`, `app/services/logical_execution_service.py`, `app/utils/parsers/*`, `app/repositories/broker_raw_transaction_repository.py`, `app/models/broker_raw_transaction.py`, `app/schemas/broker_raw_transaction.py`, `app/api/v1/imports.py`, `app/api/v1/broker.py`; new package `app/services/brokers/`.
- Database: one Alembic migration (3 nullable/defaulted columns + data backfill). Reversible.
- API/OpenAPI: unchanged. Frontend: unchanged.
- Tests: new golden-master characterization suite that must stay green across the refactor.
- Docs: `AGENTS.md` broker-ingestion section updated to describe the adapter contract.
