## Context

After `broker-adapter-architecture`, a broker is one adapter in `backend/app/services/brokers/` producing a `CanonicalImportBatch` of `BrokerRawTransactionCreate` (now with `order_id`, `net_cash`, `is_mixed_execution`). This change adds a `generic` adapter whose input format is the public, versioned projection of that canonical execution — so there is no third format to keep in sync.

Relevant facts from the code:
- Raw IDs are `{user_id}:{broker}:{tx_id}` (`import_service.py:405`) — unique per **user**, not per account. Inserts use `ON CONFLICT (id) DO NOTHING` (`broker_raw_transaction_repository.py:72`), so a collision silently drops data.
- FIFO lot key is `(symbol, conid, asset_class)` (`aggregator.py:679`). IBKR stores options as underlying + `conid`; Schwab stores the OCC symbol with `conid=NULL`.
- Corporate actions are per user and the IBKR path **overwrites** an existing split's ratio (`import_service.py:~391`).
- `AccountType` is a PostgreSQL enum `accounttype`.
- Help content lives in `frontend/lib/help-content`; import capability descriptor in `frontend/components/imports/ImportCapability.ts`.

## Goals / Non-Goals

**Goals:**
- Any broker's data can be imported via a documented JSON/CSV format with the same guarantees as native imports.
- Silent data loss is impossible: duplicates in a file, cross-account ID collisions and strategy switches are all rejected loudly.
- The user sees what will happen (preview) before anything is written.

**Non-Goals:**
- No broker-specific converters (Tastytrade etc.) — users or future adapters produce the format.
- No cash movements, dividends, interest, transfers — executions and splits only.
- No mixing of generic files into IBKR/Schwab accounts.
- No in-place editing of previously imported generic executions via re-upload (raw layer is immutable; corrections go through the existing suppress/edit features).

## Decisions

### D1 — Format = public projection of the canonical execution
Pydantic models `GenericExecutionDocumentV1`, `GenericExecutionV1`, `GenericOptionV1`, `GenericSplitV1` in `app/schemas/generic_import.py` with `extra="forbid"`. They are the single source for validation, OpenAPI component, JSON Schema endpoint, docs tests and the CSV template. Field names are snake_case English and broker-neutral (`side`/`position_effect` rather than `direction`/`open_close`, because users think in buy/sell and open/close).

*Alternative:* expose `BrokerRawTransactionCreate` directly — rejected; it contains internal fields (`user_id`, `raw_data`, composite `id`) and would freeze internal naming into a public contract.

### D2 — `external_id` vs `order_id`
They are distinct: `external_id` identifies one fill (idempotency), `order_id` groups fills/legs of one order (combo detection). Duplicate `external_id` in a file is a hard error because `ON CONFLICT DO NOTHING` would otherwise silently drop the second partial fill.

### D3 — Account-scoped raw IDs
`{user_id}:generic:{account_id}:x:{external_id}` / `...:f:{sha256}:{ordinal}`. Max length 36+1+7+1+36+3+100 = 184 ≤ 200 (`_EXEC_ID_MAX_LENGTH`). The `x:`/`f:` infix makes the strategy visible in the ID and prevents an external ID from ever colliding with a fingerprint.

*Alternative:* namespace by the free-text `source` — rejected; typos ("tastytrde") would create duplicates and two accounts at the same broker would still collide.

### D4 — Fingerprint + ordinal, strategy locked per account
Fingerprint inputs exclude commission/pnl/position_effect/order_id (restatable or derived fields). The ordinal handles identical partial fills within one file. Known limitation (documented): if two overlapping files contain *different numbers* of otherwise identical fills in the overlap, ordinals diverge; the preview makes this visible ("already imported" count lower than expected). Strategy lock is stored as an `AccountProperty` entry `generic_id_strategy` via the existing encrypted-property helpers (all `AccountProperty` values are Fernet-encrypted; harmless for a non-secret, and it avoids a schema change); reset by the clear-all-trades service.

*Alternative:* require `external_id` always — rejected by user; users without broker IDs would invent unstable ones (row numbers), which is worse than a deterministic fingerprint.

### D5 — Contract identity
`conid = contract_id` if provided; else for options `"{symbol}:{YYYYMMDD}:{C|P}:{strike.normalize()}"`; else `NULL`. Symbol for options is the underlying (IBKR convention), so generic trades display like IBKR trades. Futures without `contract_id` rely on the symbol including the contract month (documented).

### D6 — Validation is all-or-nothing, outside the transaction
The adapter's `parse` raises a structured `GenericFormatValidationError(errors=[...])` before `import_trades` writes anything; the route maps it to HTTP 422 with the error list. Error messages contain field names and codes only (audit/sensitive-data policy).

JSON is parsed with `json.loads(..., parse_float=Decimal, parse_int=...)` to keep decimals lossless. CSV via `csv.DictReader` on `utf-8-sig`.

### D7 — Preview reuses the adapter, not the pipeline
`ImportPreviewService` (new, in `services/`): resolve adapter → `parse` → compute raw IDs (same function the pipeline uses — moved to a shared helper so preview and import cannot diverge) → one `SELECT id, suppressed, deleted FROM broker_raw_transactions WHERE id = ANY(:ids)` → split comparison. It does not run aggregation; it reports raw-level novelty, which is what determines whether trades change.

### D8 — Splits insert-only for generic
The generic adapter marks its batch's corporate actions as `insert_only`; the pipeline's corporate-action upsert honours a batch-level policy (`ImportPolicy.corporate_actions_overwrite: bool`, `True` for IBKR to preserve behavior, `False` for generic). Conflicts become warnings.

### D9 — Publication
- OpenAPI: `GenericExecutionDocumentV1` registered as response model of `GET /imports/formats/generic` (returns `model_json_schema()`), so it appears in components and the generated TS client.
- `GET /imports/formats/generic/template.csv`: static content generated from model field order; tested to parse.
- `docs/import-generic-format.md`: field table, JSON + CSV examples, ID-strategy explanation, limitations, conversion tips (spreadsheet, script, LLM prompt).
- Help: new section "Import from other brokers" in `frontend/lib/help-content` linking the template and schema.
- A docs test loads the examples from the markdown fence blocks and validates them against the models.

## Risks / Trade-offs

- [Fingerprint ordinal divergence across overlapping files] → preview counts + documented guidance ("export non-overlapping ranges or use external IDs").
- [User supplies wrong `position_effect`] → FIFO still runs; open/close mismatches surface as orphan lots/warnings exactly as with brokers. Documented as "omit if unsure".
- [Netcash sign mismatch breaks combo direction] → equivalence test against IBKR fixtures covers combos.
- [Enum migration not reversible in PostgreSQL] → downgrade is a documented no-op; the value is harmless when unused.
- [Large CSVs] → existing `IMPORT_MAX_FILE_SIZE_MB` limit applies; validation is linear.

## Migration Plan

1. Alembic: `ALTER TYPE accounttype ADD VALUE 'GENERIC'` (outside a transaction block per PostgreSQL rules for older versions; follow db-migration skill).
2. Backend deploy (adapter, endpoints). 3. openapi-sync + frontend deploy.
Rollback: revert code; unused enum value remains.

## Open Questions

- Should a later version allow cash transactions/dividends? (Explicitly out of v1.)
- Should the format version be echoed in `ImportResult`? (Nice-to-have; not required.)
