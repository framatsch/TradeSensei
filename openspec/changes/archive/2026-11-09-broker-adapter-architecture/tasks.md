## 1. Safety net (before any production code changes)

- [x] 1.1 Create an anonymized Schwab fixture file under `backend/tests/fixtures/schwab/` covering equity round-trip, single option, multi-leg option order, partial fills, and a multi-account wrapped payload (derived from the inline payloads in `test_schwab_json_import.py`)
- [x] 1.2 Implement the normalized snapshot serializer (stable sort, UUID→ordinal, ISO-UTC timestamps, Decimals as strings) in `backend/tests/utils/`
- [x] 1.3 Add `backend/tests/integration/test_import_golden_master.py`: first import, second import (idempotency), and protected-trade re-import (open + closed trade with notes/tags/playbook) for every IBKR fixture in `backend/tests/fixtures/ibkr/` and every Schwab fixture
- [x] 1.4 Generate and commit the snapshot JSON files on the unmodified code; run the suite twice to prove determinism
- [x] 1.5 Add a golden-master case for IBKR Flex sync (mocked `FlexImportService`) and for the `/schwab-json` body endpoint
- [x] 1.6 Run the full backend suite + `mypy --strict` + `ruff` and record the baseline (lint-check, unit-test skills)

## 2. Broker-neutral raw fields (L4, L5)

- [x] 2.1 Verify the exact normalization used by `get_combo_order_meta_by_raw_ids` and `LogicalExecutionService` for `brokerageOrderID`, `netCash`, `openCloseIndicator`
- [x] 2.2 Alembic migration: add `order_id`, `net_cash`, `is_mixed_execution` to `broker_raw_transactions` with backfill matching 2.1; reversible downgrade (db-migration skill)
- [x] 2.3 Add the three fields to the ORM model and `BrokerRawTransactionCreate`; remove the `is_mixed_execution` property
- [x] 2.4 Populate the fields in `IBKRXMLParser.parse_raw`; Schwab sets `order_id=None`, `net_cash=None`, `is_mixed_execution=False` explicitly
- [x] 2.5 Switch `LogicalExecutionService` and `get_combo_order_meta_by_raw_ids` / `import_service.py:1900` to the columns
- [x] 2.6 Migration test: seed DB from fixtures with pre-migration schema, upgrade, assert backfilled values and identical combo groupings
- [x] 2.7 Golden master green (snapshots may only gain the three new raw columns — review diff manually)

## 3. Adapter contract and registry

- [x] 3.1 Create `backend/app/services/brokers/contracts.py`: capability Protocols, `CanonicalImportBatch`, `ImportPolicy`, `BindingResult`, `FetchedPayload`
- [x] 3.2 Create `registry.py` with `get_adapter(key)`, `adapter_for_account_type(type)`, `UnsupportedBrokerError` semantics identical to `factory.get_parser`
- [x] 3.3 IBKR adapter: file import wrapping `IBKRXMLParser.parse_raw` returning warnings in the batch; policy self-heal `False`
- [x] 3.4 Schwab adapter: file import wrapping `SchwabJSONParser.parse_raw`; policy self-heal `True`
- [x] 3.5 Unit tests for registry resolution, unknown key, account type without adapter, extension sets

## 4. Pipeline de-branching (L1, L2, L3, L6)

- [x] 4.1 Move Schwab decode/select/bind + audit emission into the Schwab adapter's `AccountBindingCapability`; `import_trades` calls it generically
- [x] 4.2 Replace the `broker == SCHWAB` self-heal guard with `adapter.policy.self_heal_pending_protected_close`
- [x] 4.3 `import_trades` obtains `CanonicalImportBatch` from `adapter.file_import.parse`; warnings taken from the batch
- [x] 4.4 Remove the legacy `parse()` fallback branch and the `enrich_pnl_eur` hook; remove `parse()` from parsers if no remaining callers (update/remove affected unit tests only where they test the deleted path)
- [x] 4.5 Add the "no broker branching" unit test (source of `import_service.py` must not reference broker/account-type members)
- [x] 4.6 Golden master + full suite + mypy green

## 5. Sync, connection and API dispatch (L7, L8)

- [x] 5.1 IBKR adapter `RemoteSyncCapability` wrapping `FlexImportService` (unchanged HTTP behavior, retries, error mapping)
- [x] 5.2 Schwab adapter `RemoteSyncCapability` (token refresh + transactions fetch moved from `_sync_schwab`)
- [x] 5.3 Move Schwab OAuth (authorize, complete, callback, status, disconnect, token storage) and connection tests into the adapters; `BrokerService` becomes a thin dispatcher
- [x] 5.4 `api/v1/imports.py` and `api/v1/broker.py` derive extensions / account-type mapping from the registry; delete `_BROKER_ALLOWED_EXTENSIONS` and `_ACCOUNT_TYPE_BROKER`
- [x] 5.5 Remove `utils/parsers/factory.py` once no callers remain (`BrokerType` keys move to the registry)
- [x] 5.6 Verify OpenAPI output is unchanged (diff `openapi.json` before/after)
- [x] 5.7 Golden master + `test_broker_service.py` + full suite + mypy green

## 6. Review and docs

- [x] 6.1 code-reviewer pass focused on behavior preservation, audit coverage and layering
- [x] 6.2 Update AGENTS.md "Broker Ingestion Paths": describe the adapter contract and "how to add a broker" checklist
- [x] 6.3 CHANGELOG `[Unreleased]` entry (Changed: internal broker adapter architecture; no user-facing change)
