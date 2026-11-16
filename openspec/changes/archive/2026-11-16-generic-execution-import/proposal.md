## Why

Only IBKR and Schwab exports can be imported today. Users of any other broker (Tastytrade, eToro, Trade Republic, …) have no way to bring their executions into Trade Sensei except manual entry. A documented, broker-neutral execution file format (JSON and CSV) lets users convert any broker export once — with a script, spreadsheet or LLM — and upload it through the same pipeline, getting every protection the native imports have (idempotency, protected trades, combos, splits). Depends on `broker-adapter-architecture`: the generic format is implemented as just another adapter.

## What Changes

- New account type `GENERIC` ("Other broker"). Generic files can only be imported into `GENERIC` accounts; `GENERIC` accounts accept no other format and have no remote sync.
- New **Trade Sensei Execution Format v1** (`tradesensei.executions`), in JSON (executions + optional splits) and CSV (executions only). Fields map 1:1 onto the canonical raw execution: `external_id`, `executed_at`, `symbol`, `asset_class`, `side`, `position_effect`, `quantity`, `price`, `commission`, `currency`, `multiplier`, `order_id`, `contract_id`, option fields, `realized_pnl`.
- New `generic` broker adapter (file import only) that validates the format strictly and all-or-nothing, and maps it to the canonical batch.
- Idempotency: `external_id` when the broker provides IDs; otherwise a deterministic **fingerprint** with in-file ordinal. The ID strategy is fixed per account by its first import. Raw IDs are namespaced by account to prevent cross-account collisions.
- New **dry-run preview** endpoint: validates the file and reports new / already-imported / suppressed counts and the ID strategy before anything is written.
- Splits in generic files are **insert-only**: an existing split with a different ratio is never overwritten, only reported as a warning.
- Format is published as an OpenAPI component and JSON Schema (`GET /api/v1/imports/formats/generic`), with a downloadable CSV template and example JSON.
- Documentation: `docs/import-generic-format.md`, a Help page section, and an inline "Format" link + template download in the import dialog for `GENERIC` accounts.
- Frontend: `GENERIC` account creation, `.json/.csv` upload, preview-then-confirm flow.

## Capabilities

### New Capabilities
- `generic-execution-format`: Definition, validation rules and publication (OpenAPI/JSON Schema, template, docs) of the Trade Sensei Execution Format v1.
- `generic-execution-import`: Importing generic files into `GENERIC` accounts — ID strategy, fingerprinting, preview, split handling, UI flow.

### Modified Capabilities
- `account-management`: Account type enumeration extended with `GENERIC`.

## Impact

- Backend: new `app/services/brokers/generic/` adapter, `app/schemas/generic_import.py`, new routes in `app/api/v1/imports.py`, `AccountType` enum; `ImportService` untouched except for consuming the preview helper.
- Database: Alembic migration adding `GENERIC` to the `accounttype` PostgreSQL enum (non-reversible enum value add; downgrade documented as no-op).
- API: new endpoints `POST /portfolios/{portfolio_id}/imports/preview`, `GET /imports/formats/generic`, `GET /imports/formats/generic/template.csv`; existing `/upload` accepts `.json`/`.csv` for `GENERIC` accounts. Frontend client regenerated (openapi-sync).
- Frontend: account create/edit modals, `ImportCapability.ts`, `ImportForm.tsx`, help content.
- Docs: new format guide, `docs/api-usage.md`, user guide, CHANGELOG.
