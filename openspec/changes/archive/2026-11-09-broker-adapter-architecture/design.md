## Context

`ImportService.import_trades()` (`backend/app/services/import_service.py:193`, ~1000 lines) is already the single terminus for all ingestion paths (see AGENTS.md "Broker Ingestion Paths" and `openspec/changes/archive/2026-08-24-unified-ibkr-import-pipeline`). Downstream of `parser.parse_raw()` the pipeline is mostly broker-neutral and operates on `BrokerRawTransactionCreate`. The remaining broker leaks are:

| # | Location | Leak |
|---|----------|------|
| L1 | `import_service.py:308-333` | Schwab payload decode, account-entry selection and `account_number` binding inline in `import_trades` |
| L2 | `import_service.py:450` | `broker == BrokerType.SCHWAB` guard on the pending-protected-close self-heal (added by `f5e44d4`, task 9.8 of `2026-09-07-closeable-protected-open-positions`; the guard exists to keep ordinary zero-insert imports query-free, not for correctness) |
| L3 | `import_service.py:~601`, `~854` | Legacy `parse()` fallback; unreachable because both parsers implement `parse_raw()` |
| L4 | `logical_execution_service.py:97-101`, `BrokerRawTransactionCreate.is_mixed_execution` | Position-flip detection reads IBKR `raw_data["openCloseIndicator"]` |
| L5 | `broker_raw_transaction_repository.py:~233-250`, `import_service.py:1900` | Combo grouping reads IBKR `raw_data["brokerageOrderID"]` / `["netCash"]` via JSONB |
| L6 | `import_service.py` (`getattr(parser, "warnings", [])`), `base.py` `enrich_pnl_eur` | Warnings via mutable parser state; a never-overridden async hook |
| L7 | `api/v1/imports.py:64-73` | Local `AccountType→BrokerType` and `BrokerType→extensions` tables |
| L8 | `broker_service.py:107-156` and Schwab OAuth methods | `if/elif` dispatch on `AccountType`; Schwab OAuth and IBKR Flex wiring inside `BrokerService` |

Constraint from the user: the refactor must be bulletproof — no regressions in imports, protection, combos, or idempotency.

## Goals / Non-Goals

**Goals:**
- One adapter per broker; adding a broker means adding one adapter package and one registry entry.
- Zero broker conditionals in `ImportService`.
- Broker-neutral raw fields for order grouping, net cash and position flips.
- Byte-for-byte identical import results on all existing fixtures (golden master).

**Non-Goals:**
- No new broker, no generic file format (that is `generic-execution-import`).
- No change to API paths, OpenAPI schemas, raw transaction ID formats, or frontend.
- No decomposition of the 1000-line `import_trades` body beyond removing the leaks — splitting the aggregation/protection logic is a separate, later concern.
- No change to Schwab's option symbol convention (Schwab stores the OCC symbol as `symbol` with `conid=NULL`; IBKR stores the underlying with `conid`). Noted, intentionally untouched.

## Decisions

### D1 — Adapter = capabilities, not a fat base class
```
backend/app/services/brokers/
├── registry.py          # BrokerKey → adapter; AccountType → BrokerKey
├── contracts.py         # Protocols + CanonicalImportBatch + ImportPolicy
├── ibkr/adapter.py      # FileImport + RemoteSync (Flex) + Connection
└── schwab/adapter.py    # FileImport + RemoteSync + Connection (OAuth) + AccountBinding
```
Capabilities are `typing.Protocol`s, checked via explicit accessor methods on the adapter (`adapter.file_import -> FileImportCapability | None`), not `isinstance` on runtime-checkable protocols, so mypy `--strict` sees the optionality.

- `FileImportCapability`: `accepted_extensions: frozenset[str]`, `parse(content: bytes, filename: str) -> CanonicalImportBatch` (pure, no DB).
- `AccountBindingCapability`: `async bind(content: bytes, account: Account, session) -> BindingResult(content, bound_account_number | None)`.
- `RemoteSyncCapability`: `async fetch(account, window) -> FetchedPayload(content, filename)`.
- `ConnectionCapability`: `test`, plus Schwab-specific OAuth operations on the Schwab adapter's own interface (routes in `api/v1/broker.py` call the Schwab adapter directly — the callback URL is Schwab-registered and stays Schwab-specific).
- `ImportPolicy`: frozen dataclass; currently one field `self_heal_pending_protected_close: bool`.

Pure parsing stays in `app/utils/parsers/` (no DB, no HTTP). Adapters live in `services/` because binding, sync and auth need the session/HTTP. This respects the layer model.

*Alternative considered:* a single abstract `BrokerAdapter` with all methods raising `NotImplementedError` — rejected; that is today's `parse_raw` pattern and is what made the dead fallback (L3) possible.

### D2 — Canonical batch reuses `BrokerRawTransactionCreate`
`CanonicalImportBatch(executions: list[BrokerRawTransactionCreate], corporate_actions: list[CorporateActionCreateRequest], warnings: list[str])`. No new execution DTO — AGENTS.md explicitly forbids introducing a third format. `BrokerRawTransactionCreate` gains `order_id`, `net_cash`, `is_mixed_execution` as real fields; the `is_mixed_execution` property is removed.

### D3 — Explicit columns + backfill migration (L4, L5)
Add `order_id VARCHAR(100) NULL`, `net_cash NUMERIC NULL` (same precision as `price`), `is_mixed_execution BOOLEAN NOT NULL DEFAULT false` to `broker_raw_transactions`. Data migration in the same revision:
```sql
UPDATE broker_raw_transactions SET
  order_id = NULLIF(raw_data->>'brokerageOrderID', ''),
  net_cash = NULLIF(raw_data->>'netCash', '')::numeric,
  is_mixed_execution = upper(coalesce(raw_data->>'openCloseIndicator','')) ~ '(C;O|O;C)';
```
The cast must mirror the repository's current cast exactly (verify against `get_combo_order_meta_by_raw_ids` before writing). Downgrade drops the columns (data is still in `raw_data`).

*Alternative considered:* keep the values in `raw_data` under neutral keys — rejected; a generic adapter would have to fake IBKR keys, and JSONB reads are untyped.

### D4 — Schwab binding moves to the adapter (L1)
`import_trades` calls `adapter.account_binding.bind(...)` when present, before `parse`. The audit emission (`_emit_account_number_bound_audit`) moves with it. Error types and HTTP mapping stay identical.

### D5 — Self-heal as policy flag (L2)
`if adapter.policy.self_heal_pending_protected_close and account_id is not None and not (...)`. Schwab: `True`; IBKR: `False`. Behavior identical. Whether to enable it for all brokers is deferred (it was a one-off repair for pre-fix data).

### D6 — Remove dead paths (L3, L6)
Delete the legacy `parse()` branch in `import_trades` and the `enrich_pnl_eur` hook. Before deletion, add a test asserting every registered file adapter returns a batch (guards against reintroducing the fallback). Keep `parse()` on parsers only if referenced elsewhere (tests/tools) — verify with grep; otherwise remove.

### D7 — Golden master first
Before any production code moves, add `backend/tests/integration/test_import_golden_master.py`:
- For every fixture under `backend/tests/fixtures/ibkr/` and the Schwab fixtures: import into a fresh account, serialize a normalized snapshot (sorted by stable keys; UUIDs replaced by ordinal references; timestamps in ISO-UTC; Decimals as strings) of raw transactions, logical executions, trades incl. combo legs, and `ImportResult` (counts + warnings).
- Second-import snapshot (idempotency) and protected-trade re-import snapshot.
- Snapshots committed as JSON files; the test compares exactly.
Each subsequent task must keep this suite green; snapshot files may only change in the migration task, and only by adding the three new columns.

## Risks / Trade-offs

- [Backfill differs from runtime extraction, e.g. empty strings or non-numeric `netCash`] → Migration uses the same normalization as the repository; integration test runs the migration on a DB seeded from fixtures and compares combo groupings before/after.
- [Hidden callers of `parse()` or `get_parser`] → grep + mypy; the factory remains as a thin wrapper over the registry until all callers are migrated, then removed in the last task.
- [Circular imports between `services/brokers` and `import_service`] → adapters do not import `ImportService`; `BrokerService` orchestrates fetch → import.
- [Warning text/order drift breaks golden master] → that is the point; any drift is a regression to investigate, not to re-snapshot.
- [Large refactor in a hot path] → tasks are ordered so each step is independently shippable and verified (golden master + full suite + mypy) before the next.

## Migration Plan

1. Deploy migration (additive columns + backfill) — safe with old code (columns unused).
2. Deploy code reading the columns.
3. Rollback: revert code; downgrade migration drops columns; `raw_data` still holds the source values.

## Open Questions

- Should the self-heal policy later become default-on for all adapters? (Out of scope; revisit after `generic-execution-import`.)
