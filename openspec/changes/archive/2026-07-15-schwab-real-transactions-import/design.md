## Context

Two Schwab import paths exist today and diverge:

- **File upload** (`POST /api/v1/imports/upload`, `schwab-json`) → `SchwabJSONParser.parse_raw()` → raw-transaction layer → FIFO aggregation (`aggregate_executions_fifo_with_sources`).
- **Online sync** (`BrokerService._sync_schwab`) → `SchwabClient.get_orders` (Orders API) → `SchwabOrderNormalizer` → direct `Trade` rows (no FIFO, no raw layer).

The parser's `_extract_instrument` reads `instruction` from each `transferItems` leg and `_map_direction` returns `None` when it is missing. Real Schwab transactions (from `schwab_cli.py` / the Transactions API, per `docs/spec/schwab/tramsaction_spec.md`) carry `instruction` only on OPTION instrument objects — equity legs expose only `positionEffect` (`OPENING`/`CLOSING`) and a signed `amount`/`cost`. Every real equity transaction therefore skips.

The upload path already validates and selects the account entry via `ImportService._select_schwab_account_entry` (match configured `account_number`; auto-bind on single account; abort on ambiguity). The online sync has no equivalent and does not know the Schwab `accountHash` required by the Transactions API.

Constraints (AGENTS.md): `Decimal` for money, timezone-aware UTC, layered architecture (no business logic in routes, no DB queries in services beyond repositories), `mypy --strict`, audit-logging policy for account mutations.

## Goals / Non-Goals

**Goals:**
- Real Schwab exports (CLI file and API transactions) import with zero "unknown instruction" warnings and correct LONG/SHORT direction.
- Online sync uses the Transactions API + `SchwabJSONParser` + FIFO pipeline — one code path shared with upload.
- Online sync resolves `accountHash` from the accounts endpoint and applies the same account-number matching semantics as upload, aborting clearly on ambiguity.
- Test fixtures reflect the real Schwab schema; a real-export regression fixture guards against recurrence.

**Non-Goals:**
- No change to public REST contracts or the upload endpoints' request/response shapes.
- No multi-leg/combo option grouping by `orderId` (out of scope; single-leg executions only, as today).
- No new persisted credentials beyond what already exists; `accountHash` is resolved at sync time, not stored.
- No change to IBKR sync.

## Decisions

**1. Direction from `cost` sign + `positionEffect` matrix (fallback), `instruction` preferred when present.**
In real Schwab data `amount` is the positive share **quantity** (e.g. `10.0`), not a signed buy/sell indicator — the monetary direction lives in `cost` (and `netAmount`): a negative `cost` is a cash outflow (buy), a positive `cost` is a cash inflow (sell). When `instruction` is absent, the parser SHALL therefore derive `direction` and the FIFO role from a combined matrix of the `cost` sign and `positionEffect`:

| `cost` sign (action) | `positionEffect` | resulting `direction` | FIFO role |
| :--- | :--- | :--- | :--- |
| `cost < 0` (buy) | `OPENING` | `LONG` | open |
| `cost < 0` (buy) | `CLOSING` | `SHORT` | cover (short close) |
| `cost > 0` (sell) | `OPENING` | `SHORT` | short open |
| `cost > 0` (sell) | `CLOSING` | `LONG` | sell close |

`quantity = abs(amount)` and `price = abs(price)` always. `positionEffect == "CLOSING"` sets `pnl = Decimal("0")` (broker-realized placeholder), else `None`. When `instruction` is present (OPTION legs, legacy fixtures) the existing instruction→direction mapping is used unchanged. Fall back to `netAmount` sign when `cost` is absent/zero.
_Alternatives considered_: (a) derive direction from the sign of `amount` — rejected because `amount` is the (positive) quantity, not a signed money value; (b) derive direction purely from `positionEffect` — rejected because `positionEffect` alone cannot distinguish a LONG close (sell) from a SHORT open (sell); the `cost` sign disambiguates.

**2. Filter trade legs to `EQUITY`/`OPTION`; treat `CURRENCY` legs only as fees.**
Real transactions list commissions/regulatory fees as separate `CURRENCY` `transferItems` with a `feeType`. The primary execution leg is the first leg whose `assetType` is `EQUITY` or `OPTION` with a non-empty symbol. Fee legs (`CURRENCY` + `feeType`) are summed as `abs(cost)` into `commission`. `OPT_REG_FEE` is added to the fee-type set.

**2a. Fee-only / cash-only transactions are silently ignored.**
Real exports contain transactions consisting **exclusively** of `CURRENCY` legs (ADR fees, interest, taxes) with no `EQUITY`/`OPTION` instrument. These SHALL be skipped silently (no execution created) rather than emitting a spurious "indeterminate direction" warning for the `activityId`.

**2c. Futures are explicitly skipped with a warning (deferred).**
`FUTURE` and `FUTURE_OPTION` legs are **not** supported in this change and SHALL NOT be treated as fee/cash-only. They are skipped with exactly one warning per transaction naming the `activityId` (e.g. "Schwab futures not yet supported"), so the skip is visible rather than a silent data loss.
_Rationale_: Correct futures P&L requires the contract `multiplier` (e.g. ES=50, CL=1000) and the futures symbol/expiry matching key, whose exact field locations are undocumented in `docs/spec/schwab/tramsaction_spec.md` and unverifiable without a real Schwab futures payload (none exists in the repo). Hard-coding `multiplier=1` would produce P&L wrong by the contract factor. Full support is a follow-up change once a real futures export is available. `AssetClass.FUTURE` already exists in the model, so no schema change is needed later.

**2b. Strict top-level status filtering.**
Only transactions whose top-level `status` is exactly `"VALID"` or `"COMPLETED"` are processed. Any other status (`PENDING`, `CANCELLED`, `UNKNOWN`, …) is skipped **without** a warning, preventing phantom trades from pending/cancelled orders.

**3. Online sync switches to the Transactions API and reuses the parser.**
`_sync_schwab` builds a wrapped payload `{accounts:[{accountNumber, transactions}]}` from the API response and feeds it through the existing raw-import pipeline (same as `POST /imports/schwab-json`). This unifies behavior, gains correct short handling, and removes the parallel normalizer.
- **Pagination**: `get_transactions` SHALL iteratively resolve any next-page token / `Link` header the Transactions API returns and concatenate all pages before handing the merged transaction list to the parser.
- **Date normalization**: `startDate`/`endDate` SHALL be formatted strictly to the format the Schwab API accepts (`YYYY-MM-DDTHH:MM:SSZ` without milliseconds) before the call, to avoid `400 Bad Request`.
_Alternative considered_: keep the Orders API and only fix the parser. Rejected — leaves two divergent paths and the short-trade bug in sync, contradicting the stated goal.

**4. Resolve `accountHash` at sync time via the accounts endpoint.**
Add `SchwabClient.get_account_numbers(access_token)` → list of `{accountNumber, hashValue}`. `BrokerService._sync_schwab` resolves the hash by matching `Account.account_number`:
- configured number matches one entry → use its hash;
- configured number set but no match → abort (`ConfigurationError`) naming configured number and available numbers;
- number unset and exactly one broker account → use it and persist `account_number` onto the `Account` row (audit event `account.account_number_bound`);
- number unset and multiple accounts → abort with: "Multiple Schwab accounts found — no assignment possible. Please enter the account number. Available: [...]".
This mirrors `ImportService._select_schwab_account_entry`; the shared decision logic is factored into a small helper to avoid divergence.

**5. Correct the Schwab base URL.**
`SchwabClient` currently targets `https://api.schwab.com/v1`, which does not match the documented `https://api.schwabapi.com/trader/v1`. Update the base URL and endpoint paths (`/accounts/accountNumbers`, `/accounts/{hash}/transactions?types=TRADE&startDate=&endDate=`).

**6. Remove dead code after cutover.**
Delete `SchwabOrderNormalizer`, `BrokerService._import_orders`, and `SchwabClient.get_orders`. `_test_schwab` (connection test) is repointed to a lightweight `get_account_numbers` call.

## Risks / Trade-offs

- **Ambiguous `cost` sign in edge transactions (e.g. `cost == 0` and `netAmount == 0`)** → Mitigation: prefer `instruction` when present; else fall back to `netAmount` sign; if still undetermined, skip with a warning naming `activityId` (existing skip behavior preserved). Fee-only/cash-only transactions are excluded from this warning path (Decision 2a).
- **Fixture rewrite invalidates aggregation expectations** → Mitigation: recompute expected P&L/counts from the reformatted fixture; add a real-export regression fixture asserting 0 warnings and correct raw-record count.
- **Schwab base-URL/endpoint change is not exercisable without live credentials** → Mitigation: unit-test client methods against mocked `httpx` responses; account-resolution logic tested with mocked `get_account_numbers`; live call validated manually during rollout.
- **Auto-bind of `account_number` during sync mutates account state** → Mitigation: only on the unambiguous single-account case, emitted with an audit event, identical to the established upload behavior.
- **Removing `SchwabOrderNormalizer` could break unreferenced callers** → Mitigation: reference search before deletion; adjust `_test_schwab` in the same change.

## Migration Plan

1. Land parser changes (Part A) — backwards-compatible: legacy `instruction` fixtures still parse.
2. Add client methods + base-URL fix; switch `_sync_schwab` and `_test_schwab`; remove dead code (Part B).
3. Reformat fixtures and add regression tests (Part C).
4. Deploy backend; no DB migration required. Rollback = revert the change (no schema/state changes persisted beyond the pre-existing `account_number` auto-bind).

## Open Questions

- None blocking. The Schwab `accountHash` is resolved live (not stored); if a future change wants to cache it, that is a separate proposal.
