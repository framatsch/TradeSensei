## Why

The `SchwabJSONParser` derives trade direction solely from an `instruction` field that exists only in synthetic test fixtures and in Schwab OPTION legs — it is absent from real Schwab equity transactions produced by `schwab_cli.py` and the Schwab Transactions API. As a result every real transaction is skipped with an "unknown instruction" warning, so genuine broker exports cannot be imported. Additionally, the online sync uses a divergent code path (Orders API + `SchwabOrderNormalizer`) that also mishandles short trades, contradicting the goal that online sync loads the same transactions through the same pipeline as the file upload.

## What Changes

- Make `SchwabJSONParser` derive execution direction from the sign of `amount` (buy/sell) plus `positionEffect` (opening/closing) when `instruction` is absent, while keeping `instruction` support for OPTION legs and legacy fixtures.
- Restrict trade-leg extraction to `assetType ∈ {EQUITY, OPTION}` (never treat `CURRENCY` legs as executions) and add `OPT_REG_FEE` to the commission fee-type set. `FUTURE`/`FUTURE_OPTION` legs are explicitly skipped with a warning (full futures support deferred to a follow-up change — see design.md).
- Harden execution-date parsing with a `time → tradeDate → transactionDate` fallback and correct `+0000` (no-colon) offset normalization.
- **BREAKING** (internal): Replace the online Schwab sync path — fetch transactions from the Schwab Transactions API and run them through `SchwabJSONParser.parse_raw()` + the FIFO pipeline instead of the Orders API + `SchwabOrderNormalizer`.
- Resolve the target `accountHash` for online sync by calling the Schwab accounts endpoint; match against the configured `Account.account_number`; auto-bind when exactly one broker account exists; abort with a descriptive error when multiple accounts exist and none is configured.
- Remove the now-unused `SchwabOrderNormalizer`, `BrokerService._import_orders`, and `SchwabClient.get_orders`.
- Update `schwab_aggregation.json` test fixtures to the real Schwab schema and add a real-export regression fixture.

## Capabilities

### New Capabilities
<!-- None — this change modifies existing broker-import behavior. -->

### Modified Capabilities
- `schwab-json-import`: The parser SHALL derive direction from `positionEffect` + `amount` sign when `instruction` is absent, filter trade legs to `EQUITY`/`OPTION`, include `OPT_REG_FEE` in commission aggregation, and support the `time → tradeDate → transactionDate` date fallback so real Schwab exports import without warnings.
- `account-centric-broker-sync`: The Schwab online sync SHALL fetch transactions (not orders), resolve the `accountHash` via the accounts endpoint, apply account-number matching (match / single-account auto-bind / abort on ambiguity), and import via the shared `SchwabJSONParser` + FIFO pipeline.

## Impact

- **Code**: `backend/app/utils/parsers/schwab_json.py`, `backend/app/utils/schwab_client.py`, `backend/app/services/broker_service.py`; removal of `backend/app/utils/schwab_normalizer.py`.
- **Tests/fixtures**: `tests/test_data/schwab/schwab_aggregation.json` (reformatted), new real-export regression fixture, broker-sync unit tests.
- **APIs**: No public REST contract change; the `POST /api/v1/imports/upload` and `schwab-json` endpoints are unaffected. Internal Schwab client methods change.
- **Behavior**: Real Schwab CLI/API exports become importable; online sync gains correct short-trade handling and account-number-based routing.
