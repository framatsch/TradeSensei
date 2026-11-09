## 0. Prerequisite

- [ ] 0.1 `broker-adapter-architecture` is fully implemented and archived (adapter registry, canonical batch, `order_id`/`net_cash`/`is_mixed_execution` columns)

## 1. Format models and validation

- [ ] 1.1 Create `app/schemas/generic_import.py` with `GenericExecutionDocumentV1`, `GenericExecutionV1`, `GenericOptionV1`, `GenericSplitV1` (`extra="forbid"`, field descriptions for OpenAPI)
- [ ] 1.2 Cross-field validators: offset-aware `executed_at` and not > 24 h in future, `option` iff OPTION, `multiplier` required for OPTION/FUTURE, version `1.x`
- [ ] 1.3 File-level validator: duplicate `external_id`, mixed ID presence, error list shape `{row, field, code, message}` capped at 200, no values in messages
- [ ] 1.4 JSON loader with lossless Decimal parsing; CSV loader (`utf-8-sig`, header required, flattened option columns, strict number format, unknown columns rejected)
- [ ] 1.5 Unit tests for every scenario in `specs/generic-execution-format/spec.md`

## 2. Generic adapter

- [ ] 2.1 `app/services/brokers/generic/adapter.py`: file import (`json`, `csv`), policy `self_heal_pending_protected_close=False`, `corporate_actions_overwrite=False`; register for `AccountType.GENERIC`
- [ ] 2.2 Mapping to `BrokerRawTransactionCreate` incl. side/position_effect/option/conid derivation and `net_cash` sign convention (verify against IBKR fixture `netCash` values)
- [ ] 2.3 Shared raw-ID helper (account-scoped external-ID and fingerprint+ordinal) used by both pipeline stamping and preview
- [ ] 2.4 Add `ImportPolicy.corporate_actions_overwrite`; IBKR/Schwab `True` (golden master must stay green), generic insert-only with conflict warnings
- [ ] 2.5 Unit tests: mapping, conid derivation, fingerprint stability and ordinals, split policy

## 3. Account type and ID strategy

- [ ] 3.1 Alembic migration adding `GENERIC` to `accounttype` (db-migration skill); add enum member in model + schemas
- [ ] 3.2 Account creation/update: `GENERIC` requires no credentials; sync and connection test rejected as unsupported
- [ ] 3.3 ID strategy lock stored as `AccountProperty` `generic_id_strategy`; set on first successful import; mismatch → 422 `id_strategy_mismatch`; audit `account.import_strategy_set`
- [ ] 3.4 Clear-all-trades service resets `generic_id_strategy`
- [ ] 3.5 Tests for lock, mismatch, reset, audit payload

## 4. API

- [ ] 4.1 `/upload` accepts `json`/`csv` for GENERIC via registry; map `GenericFormatValidationError` → 422 with error list
- [ ] 4.2 `ImportPreviewService` + `POST /portfolios/{portfolio_id}/imports/preview` with `ImportPreviewResult` schema (no writes)
- [ ] 4.3 `GET /imports/formats/generic` (JSON Schema) and `GET /imports/formats/generic/template.csv`
- [ ] 4.4 openapi-docs pass: summaries, descriptions, response codes, examples
- [ ] 4.5 API tests: upload success, wrong account type, invalid file, preview no-write guarantee (row counts before/after), preview counts after partial re-import, schema/template endpoints

## 5. End-to-end correctness

- [ ] 5.1 Test helper converting IBKR fixture XML → generic JSON (external_id, order_id, contract_id, position_effect, splits)
- [ ] 5.2 Equivalence test: native IBKR import vs generic import of converted fixtures produce identical normalized trades (all fixtures in `backend/tests/fixtures/ibkr/`)
- [ ] 5.3 Same equivalence in fingerprint mode (external_id stripped) for fixtures without identical partial fills
- [ ] 5.4 Idempotency: re-import, overlapping windows, identical partial fills, two GENERIC accounts with same external_id
- [ ] 5.5 Protected trades: attach metadata, re-import, closing execution in a later file closes the protected open trade
- [ ] 5.6 Golden master from `broker-adapter-architecture` still green

## 6. Frontend

- [ ] 6.1 openapi-sync (regenerate client)
- [ ] 6.2 `AccountType` `generic` in types; create/edit modals offer "Other broker (generic file)" without credential fields
- [ ] 6.3 `ImportCapability.ts`: `generic` entry (no sync window); `ImportForm` accepts `.json,.csv` for generic accounts
- [ ] 6.4 Preview step: show strategy, counts, split conflicts, warnings, row errors; confirm disabled on errors or strategy conflict
- [ ] 6.5 "Format help" link and CSV template download in the import dialog
- [ ] 6.6 RTL tests for preview/confirm flow; ui-visual-check on the import dialog

## 7. Documentation

- [ ] 7.1 `docs/import-generic-format.md` (field table, JSON/CSV examples, ID strategy, limitations, conversion tips)
- [ ] 7.2 Docs test validating the guide's JSON example and the CSV template against the models
- [ ] 7.3 Help section "Import from other brokers" in `frontend/lib/help-content`
- [ ] 7.4 Update `docs/api-usage.md`, `docs/user-guide.md`, AGENTS.md (adapter list), CHANGELOG `[Unreleased]`
- [ ] 7.5 code-reviewer pass (audit coverage, sensitive data in errors, layering)
