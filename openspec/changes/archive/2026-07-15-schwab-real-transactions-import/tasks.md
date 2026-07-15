## 1. Parser — direction & extraction (backend)

- [x] 1.1 In `schwab_json.py`, extend `_extract_instrument` to select the primary leg only when `instrument.assetType` is `EQUITY` or `OPTION` with a non-empty symbol; also return `positionEffect`, `assetType`, and signed `cost` (and expose transaction `netAmount`). `FUTURE`/`FUTURE_OPTION` legs are recognized (for the skip in 1.4) but NOT selected as executions.
- [x] 1.2 Add direction resolution that prefers `instruction` when present, and otherwise derives `direction` from the combined matrix of the `cost` sign and `positionEffect` (`cost<0`+OPENING→LONG; `cost<0`+CLOSING→SHORT; `cost>0`+OPENING→SHORT; `cost>0`+CLOSING→LONG); fall back to the `netAmount` sign when `cost` is absent/zero.
- [x] 1.3 Set `quantity = abs(amount)`, `price = abs(price)`, and `pnl = Decimal("0")` when `positionEffect == "CLOSING"` (else `None`).
- [x] 1.4 Handle skip/ignore cases: (a) transactions with **only** `CURRENCY` legs (fees/interest/tax) → ignore silently, no warning; (b) top-level `status` not exactly `"VALID"`/`"COMPLETED"` → skip silently, no warning; (c) primary leg `assetType` in `{FUTURE, FUTURE_OPTION}` → skip with exactly one warning naming `activityId` ("futures not yet supported"), NOT treated as fee-only; (d) a valid `EQUITY`/`OPTION` trade leg whose direction is still indeterminate (`cost` and `netAmount` both zero) → skip with a warning naming `activityId`.
- [x] 1.5 Add `"OPT_REG_FEE"` to `_FEE_TYPES`; keep fee aggregation summing `abs(cost)` over `CURRENCY` legs with a `feeType`.
- [x] 1.6 Harden `_parse_datetime`: normalize `+0000` (no-colon) offsets and add `time → tradeDate → transactionDate` fallback in `parse_raw`.
- [x] 1.7 Verify integer `activityId` normalizes to a plain string id (`schwab:124780687237`, no decimal suffix).

## 2. Online sync — Transactions API + account resolution (backend)

- [x] 2.1 In `schwab_client.py`, correct the base URL/paths to the documented `https://api.schwabapi.com/trader/v1`.
- [x] 2.2 Add `SchwabClient.get_account_numbers(access_token)` → list of `{accountNumber, hashValue}`.
- [x] 2.3 Add `SchwabClient.get_transactions(access_token, account_hash, from_date, to_date)` calling `/accounts/{hash}/transactions?types=TRADE&startDate=&endDate=`. Format `startDate`/`endDate` strictly as `YYYY-MM-DDTHH:MM:SSZ` (no milliseconds) to avoid `400`; iteratively resolve any next-page token / `Link` header and concatenate all pages before returning the merged list.
- [x] 2.4 Factor account-number matching (match / single-account auto-bind / abort on ambiguity) into a shared helper reused by both upload and sync resolution.
- [x] 2.5 Rewrite `BrokerService._sync_schwab` to: fetch account numbers, resolve `accountHash` via the shared matcher, fetch transactions, wrap them as `{accounts:[{accountNumber, transactions}]}`, and import through the raw-transaction pipeline (`SchwabJSONParser.parse_raw` + FIFO).
- [x] 2.6 On single-account auto-bind, persist `account_number` onto the `Account` row and emit an `account.account_number_bound` audit event; on ambiguity, abort with the "multiple Schwab accounts found — enter account number" message.
- [x] 2.7 Repoint `BrokerService._test_schwab` to a lightweight `get_account_numbers` call.

## 3. Remove dead code (backend)

- [x] 3.1 Reference-search then delete `SchwabOrderNormalizer` (`schwab_normalizer.py`), `BrokerService._import_orders`, and `SchwabClient.get_orders`; update imports.

## 4. Fixtures & tests

- [x] 4.1 Reformat `tests/test_data/schwab/schwab_aggregation.json` to the real schema (no `instruction`; `positionEffect` + signed `amount`/`cost`; integer `activityId`; fees as `CURRENCY` legs).
- [x] 4.2 Recompute and update aggregation expectations (trade counts, P&L) in affected Schwab import/aggregation tests.
- [x] 4.3 Add a real-export regression fixture (trimmed copy of `tmp/cache/transactions.json`) and assert 5 raw records with zero skip warnings, correct LONG/SHORT directions from the `cost`+`positionEffect` matrix.
- [x] 4.4 Add a small `instruction`-based (OPTION) fixture/test to keep the instruction branch covered.
- [x] 4.5 Add parser edge-case tests: a fee-only (`CURRENCY`-only) transaction is ignored without warning; a `PENDING`/`CANCELLED` status transaction is skipped without warning; a `FUTURE` transaction is skipped with exactly one warning and is NOT imported as EQUITY; `OPT_REG_FEE` is summed into commission.
- [x] 4.6 Add `BrokerService` sync unit tests with mocked `get_account_numbers`/`get_transactions` covering: match, single-account auto-bind, multi-account abort, and multi-page transaction merging.

## 5. Verification

- [x] 5.1 Run `rtk pytest tests/` (Schwab parser, aggregation, broker sync) — all green.
- [x] 5.2 Run `lint-check` (ruff + mypy --strict) — zero errors.
- [X] 5.3 Manually import the real `transactions.json` via the upload path and confirm zero warnings and visible positions.
