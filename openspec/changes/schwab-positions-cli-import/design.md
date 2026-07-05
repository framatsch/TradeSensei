## Context

Schwab import currently flows: user obtains a Schwab JSON file → uploads it via `POST /imports/upload` (or `POST /imports/schwab-json`) → `SchwabJSONParser.parse_raw()` produces `BrokerRawTransaction` rows → the broker-neutral FIFO pipeline (`ImportService.import_file`) aggregates them into `Trade` rows. The parser today accepts a **bare top-level array** of transactions, using `transactionItem` (test fixture) or `transferItems` (API-ish) shapes; account matching is by `account_id` UUID only, and `Account.account_number` is dead metadata.

Two facts drive this change:

1. The real Schwab Trader API returns a **wrapped** payload — `{fetchedAt, dateRange, accounts:[{accountNumber, accountHash, positions, transactions}]}` — documented in `tmp/positions_schema.md`. Transactions live under `accounts[].transactions` and use `transferItems` legs with a `time` field (UTC offset like `+0000`).
2. There is no supported way to *get* that file. `tools/` has CLI precedent (`reset_password.py`) but no Schwab tool; `SchwabClient` only fetches orders, not positions/transactions. The user's `tmp/schwab_get_positions.py` prototype already produces the wrapped format via `schwabdev`.

Constraints (AGENTS.md): `Decimal` for money, tz-aware UTC timestamps, layered backend (parsing in `utils/parsers`, orchestration in `services`, HTTP in `api`), `mypy --strict`, surgical changes.

## Goals / Non-Goals

**Goals:**
- One-command download of the user's Schwab trades into a wrapped JSON file.
- Importer accepts **only** the wrapped format and reads transactions from `accounts[].transactions`.
- Account-number safety: abort import when the file's account(s) don't match the target account's configured `account_number`, or when the file is ambiguous (multiple accounts, no configured number).
- CLI resolves a single account: auto-select when one, `--account-id` when many, abort+list otherwise.
- Reformatted test fixture + updated unit/integration tests; user docs + tools reference.

**Non-Goals:**
- No new HTTP endpoints (reuse `upload` and `schwab-json`).
- No import of `positions` (open holdings) into any model — `positions` is written to the file for completeness but only `transactions` drive the import. Open-positions seeding is owned by the broker-neutral `open-position-seeding` contract and implemented for Schwab by the `schwab-open-position-adapter` change (see `openspec/changes/open-position-seeding/` and `openspec/changes/schwab-open-position-adapter/`), which are the intended consumers of Schwab `positions[]`.
- No backwards compatibility with the legacy top-level-array format (explicitly BREAKING).
- No changes to the FIFO aggregation, raw-transaction, or IBKR paths.
- The dead legacy CSV parser (`schwab.py`) is left untouched (flagged, not deleted, per surgical-changes rule).
- The existing "Schwab JSON Parser — Asset Class Mapping" requirement (unknown `assetType` → default EQUITY) applies to the **transaction** path only and is unchanged here. Position snapshots use a stricter EQUITY/OPTION-only mapping (skip-on-unknown) defined by `schwab-open-position-adapter`; the two paths are intentionally distinct and do not conflict.

## Decisions

### D1: Wrapped-only parser, transactions extracted from `accounts[]`
`SchwabJSONParser.parse_raw()` will require a top-level JSON **object** with an `accounts` array; a top-level array now raises `ImportParseError`. It iterates `accounts[].transactions` and reuses the existing per-transaction logic (`transferItems` leg extraction, commission summing, instruction/direction mapping). The `transactionItem` branch and its commission short-circuit are removed since the wrapped API format always uses `transferItems`.
- *Alternative — auto-detect both formats*: rejected per explicit user decision ("only new wrapped format"). Removing dual support keeps the parser and tests simpler and avoids format-sniffing ambiguity.

### D2: Datetime from `time` with UTC offset
The wrapped format uses `time: "2026-07-02T17:35:33+0000"`. The existing `_parse_datetime` already normalizes `Z` and offsets via `datetime.fromisoformat`; it needs to also handle the compact `+0000` (no colon) offset. Keep it tz-aware → UTC. The old `transactionDate`/`-05:00` fixture path is dropped.

### D3: Account-number matching lives in the service, not the parser
The parser stays broker-file-shape focused and returns raw records. Account selection + matching is an orchestration concern, so it belongs in `ImportService` (or a small helper it calls) where the `Account` row (and its `account_number`) is available. The importer will:
1. Parse the wrapped payload to a list of account entries (each with `accountNumber` + its transactions).
2. If `account.account_number` is set → pick the file account whose `accountNumber` equals it; none → abort (422) naming configured vs. file numbers.
3. If unset → exactly one file account: use it; more than one: abort (422) listing available `accountNumber`s.
- *Alternative — do matching in the parser*: rejected; the parser has no access to the target `Account` and matching is policy, not parsing. A dedicated exception type (e.g. `ImportAccountMismatchError`) mapped to HTTP 422 keeps the route thin.
- *Implementation note*: because `SchwabJSONParser.parse_raw(content, filename)` currently takes only bytes, the account-selection step will resolve the target account entry **before** parsing (or expose account metadata alongside raw records) so only the selected account's transactions are turned into raw records. The exact seam (pre-filter the payload to the chosen account vs. tag raw records by accountNumber) is settled in tasks; both keep matching in the service layer.

### D4: CLI is self-contained under `tools/`, based on the existing prototype
`tools/schwab_get_positions.py` adapts `tmp/schwab_get_positions.py`: `schwabdev` client, `.env` loading, the `schwabdev` token-exchange bugfix shim, and the redirect-URI auth helper. It writes to a `tools/`-local `cache/positions.json` (or a `--output` path). New: an `--account-id` argument (Schwab account number) with resolution logic (D5). It does **not** import backend `app.*` modules (unlike `reset_password.py`) — it only talks to Schwab and writes a file, so it needs no DB/sys.path wiring.
- *Alternative — add `get_positions` to `SchwabClient` and route through the backend*: heavier, couples the CLI to the running backend and its OAuth storage. Rejected for a download-only tool; keep it standalone and let the file be imported through the normal endpoints.

### D5: CLI account resolution
Fetch `client.linked_accounts()`. If `--account-id` given: select the linked account whose `accountNumber` matches; no match → exit non-zero listing available numbers. If omitted: exactly one linked account → use it; more than one → exit non-zero listing available numbers. This mirrors the importer's abort-on-ambiguity policy so the file the CLI writes always contains exactly one account, satisfying the importer's single-account happy path.

### D6: Test fixture reformatted to wrapped `transferItems`
`tests/test_data/schwab/schwab_aggregation.json` is rewritten as `{fetchedAt, dateRange, accounts:[{accountNumber, accountHash, positions:[], transactions:[...]}]}` with each transaction using `transferItems` (equity leg + optional fee leg) and a `time` field. The FIFO ground-truth (matched pairs, open lots) is preserved so `test_schwab_json_import_ground_truth` still asserts the same trade counts. Parser unit tests are updated to the wrapped shape; new tests cover account-number match/mismatch/ambiguity and CLI account resolution.

## Risks / Trade-offs

- **Breaking input format** → Any previously exported top-level-array files stop importing. Mitigation: clear 422 message pointing at the wrapped format; the CLI regenerates the correct file; documented in the spec's REMOVED requirement Migration note.
- **Fixture rewrite could drift from FIFO ground truth** → wrong assertions or masked regressions. Mitigation: preserve the exact symbol/side/qty/price sequence when converting each `transactionItem` to a `transferItems`-shaped transaction; run the ground-truth integration test as the gate.
- **CLI depends on Schwab OAuth + `schwabdev` quirks** (redirect-URI encoding, token-exchange `False` bug) → auth failures. Mitigation: carry over the prototype's shim and auth helper verbatim; document the manual copy-the-redirect-URL step.
- **`accountNumber` values are sensitive** → must not leak into audit logs. Mitigation: import path logs only `account_id`/`resource_id` and safe identifiers per the Audit Logging Policy; mismatch errors are returned to the caller (the owner) but not audit-logged with the number.
- **`schwab-json` endpoint currently types the body as `list[dict]`** → wrapped object body breaks the signature. Mitigation: change the body type to the wrapped object (a `dict`) and update its OpenAPI description; covered in tasks.

## Migration Plan

1. Land parser + service changes behind the same endpoints (no route additions).
2. Reformat the test fixture and update unit/integration tests in the same change so CI stays green.
3. Add the CLI tool + docs + `tools/README.md`.
4. Rollback: revert the change; the wrapped format and CLI are additive-in-tooling but breaking-in-parser, so rollback restores the top-level-array parser. No DB migration is involved (no schema change), so rollback is code-only.

### D7: Persist `accountNumber` when unset and file has one account
When `account.account_number` is unset and the file contains exactly one account, the importer SHALL write that account's `accountNumber` onto the `Account` row so subsequent imports match automatically. This makes the first successful import self-configuring while still aborting on ambiguity. The write is a normal `Account` update (audited via the standard middleware as an `account.updated`; the number itself is not placed in audit metadata).

### D8: CLI output defaults to `./tmp`
`tools/schwab_get_positions.py` writes to `./tmp/positions.json` by default, with a `--output` override. (`./tmp` is the project's scratch dir already holding the prototype and schema.)

## Open Questions

- None outstanding — resolved: (1) auto-persist `accountNumber` on first import when unset and unambiguous (D7); (2) CLI output defaults to `./tmp/positions.json` (D8).
