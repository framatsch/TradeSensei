## MODIFIED Requirements

### Requirement: Schwab JSON Parser — Instruction Mapping
The `SchwabJSONParser` SHALL determine the execution `direction` and quantity for each trade leg, reading from transactions in `accounts[].transactions`. At the raw-record level, `direction` SHALL strictly denote the **execution side** (buy → `LONG`, sell → `SHORT`); it does NOT encode the position role. The FIFO closing detection SHALL be driven by the `pnl` field (set from `positionEffect == "CLOSING"`), not by `direction`. When a leg carries an `instruction` field, the parser SHALL map it to the execution side (`BUY`/`BUY_TO_COVER`/`BUY_TO_OPEN`/`BUY_TO_CLOSE` → `LONG`; `SELL`/`SELL_SHORT`/`SELL_TO_OPEN`/`SELL_TO_CLOSE` → `SHORT`). When `instruction` is absent (real Schwab equity legs), the parser SHALL derive the execution side from the sign of `cost` (the monetary field: negative = buy → `LONG`, positive = sell → `SHORT`), falling back to the sign of `netAmount` when `cost` is absent or zero. `positionEffect` is retained only to set the `pnl` placeholder (`CLOSING` → `0`), not to alter `direction`. Quantity SHALL always be `abs(amount)` (the `amount` field is the positive share quantity, not a signed indicator).

#### Scenario: BUY instruction maps to LONG opening
- **WHEN** a transaction leg has `instruction = "BUY"`
- **THEN** the parser SHALL set the execution `direction = "LONG"` and `quantity = abs(amount) > 0`

#### Scenario: SELL instruction maps to closing sell
- **WHEN** a transaction leg has `instruction = "SELL"`
- **THEN** the parser SHALL set the execution `direction = "SHORT"` (sell side) and `quantity = abs(amount) > 0`

#### Scenario: SELL_SHORT instruction maps to SHORT opening
- **WHEN** a transaction leg has `instruction = "SELL_SHORT"`
- **THEN** the parser SHALL set the execution `direction = "SHORT"` and `quantity = abs(amount) > 0`

#### Scenario: BUY_TO_COVER instruction maps to covering buy
- **WHEN** a transaction leg has `instruction = "BUY_TO_COVER"`
- **THEN** the parser SHALL set the execution `direction = "LONG"` (buy side) and `quantity = abs(amount) > 0`

#### Scenario: Missing instruction, negative cost (buy) maps to LONG execution side
- **WHEN** a transaction leg has no `instruction` field and `cost < 0` (a buy)
- **THEN** the parser SHALL set `direction = "LONG"` (execution side) and `quantity = abs(amount) > 0`, regardless of `positionEffect`

#### Scenario: Missing instruction, positive cost (sell) maps to SHORT execution side
- **WHEN** a transaction leg has no `instruction` field and `cost > 0` (a sell)
- **THEN** the parser SHALL set `direction = "SHORT"` (execution side) and `quantity = abs(amount) > 0`, regardless of `positionEffect`

#### Scenario: positionEffect governs closing detection via P&L, not direction
- **WHEN** a transaction leg has `positionEffect = "CLOSING"` (e.g. a buy-to-cover with `cost < 0`, or a sell-to-close with `cost > 0`)
- **THEN** the parser SHALL set `direction` strictly from the execution side (buy → `LONG`, sell → `SHORT`) and SHALL set `pnl = 0` so the FIFO layer recognizes the leg as closing an existing open lot of the opposite side

#### Scenario: cost absent or zero falls back to netAmount sign
- **WHEN** a transaction leg has no `instruction` field and `cost` is absent or zero
- **THEN** the parser SHALL derive the buy/sell execution side from the sign of the transaction `netAmount` (negative → `LONG`, positive → `SHORT`)

#### Scenario: Closing positionEffect sets zero P&L placeholder
- **WHEN** a transaction leg has `positionEffect = "CLOSING"`
- **THEN** the parser SHALL set `pnl = 0` on the resulting `BrokerRawTransaction`

#### Scenario: Opening positionEffect leaves P&L unset
- **WHEN** a transaction leg has `positionEffect = "OPENING"`
- **THEN** the parser SHALL leave `pnl = null` on the resulting `BrokerRawTransaction`

#### Scenario: Direction cannot be determined is skipped
- **WHEN** a trade leg (with a valid `EQUITY`/`OPTION` symbol) has no `instruction` and both `cost` and `netAmount` are zero
- **THEN** the parser SHALL skip that record and log a warning with the `activityId`

### Requirement: Schwab JSON Parser — Transaction Extraction
The `SchwabJSONParser` SHALL extract each execution from the `transferItems` array of the transactions carried under `accounts[].transactions`. The primary execution leg SHALL be a leg whose `instrument.assetType` is `EQUITY` or `OPTION`; `CURRENCY` legs SHALL NOT be treated as executions. Fee legs SHALL be aggregated into `commission`.

#### Scenario: transferItems format (array)
- **WHEN** a transaction object has a `transferItems` key with an array of leg objects
- **THEN** the parser SHALL use the first leg whose `instrument.assetType` is `EQUITY` or `OPTION` with a non-empty `instrument.symbol` as the primary execution leg

#### Scenario: CURRENCY legs are not executions
- **WHEN** a `transferItems` leg has `instrument.assetType = "CURRENCY"`
- **THEN** the parser SHALL NOT create a `BrokerRawTransaction` execution from that leg

#### Scenario: Fee legs summed into commission
- **WHEN** one or more `transferItems` legs have `instrument.assetType = "CURRENCY"` and a `feeType` in `{COMMISSION, SEC_FEE, TAF_FEE, OPT_REG_FEE}`
- **THEN** the parser SHALL sum `abs(cost)` across those legs and store the total as `commission` on the primary execution of the same transaction

#### Scenario: time field parsed as UTC
- **WHEN** a transaction has a `time` field with a UTC offset without a colon (e.g. `+0000`)
- **THEN** the parser SHALL parse it as a timezone-aware datetime and convert to UTC

#### Scenario: Execution date fallback chain
- **WHEN** a transaction has no `time` field
- **THEN** the parser SHALL use `tradeDate`, and if that is also absent, `transactionDate`, parsing the chosen value as a timezone-aware datetime converted to UTC

## ADDED Requirements

### Requirement: Schwab JSON Parser — Fee-Only Transaction Handling
The `SchwabJSONParser` SHALL silently ignore transactions that contain no `EQUITY` or `OPTION` execution leg — i.e. transactions consisting exclusively of `CURRENCY` legs (fees, interest, taxes, ADR charges) — without emitting a warning for the `activityId`.

#### Scenario: Transaction with only CURRENCY legs is skipped silently
- **WHEN** a TRADE transaction's `transferItems` contains only `CURRENCY` legs and no leg with `assetType` in `{EQUITY, OPTION}` and a non-empty symbol
- **THEN** the parser SHALL NOT create a `BrokerRawTransaction`
- **THEN** the parser SHALL NOT append a warning for that `activityId`

### Requirement: Schwab JSON Parser — Futures Deferred
The `SchwabJSONParser` SHALL skip transactions whose primary trade leg has `assetType` in `{FUTURE, FUTURE_OPTION}`, emitting exactly one warning naming the `activityId`. Futures SHALL NOT be treated as fee-only/cash-only transactions and SHALL NOT be imported as `EQUITY`.

#### Scenario: Futures transaction skipped with warning
- **WHEN** a TRADE transaction's primary leg has `instrument.assetType` in `{FUTURE, FUTURE_OPTION}`
- **THEN** the parser SHALL NOT create a `BrokerRawTransaction`
- **THEN** the parser SHALL append exactly one warning naming the `activityId` indicating futures are not yet supported

### Requirement: Schwab JSON Parser — Strict Status Filtering
The `SchwabJSONParser` SHALL process only transactions whose top-level `status` is exactly `"VALID"` or `"COMPLETED"`, skipping all other statuses without a warning.

#### Scenario: Non-final status is skipped without warning
- **WHEN** a transaction has a top-level `status` other than `"VALID"` or `"COMPLETED"` (e.g. `PENDING`, `CANCELLED`, `UNKNOWN`)
- **THEN** the parser SHALL skip that transaction and SHALL NOT create a `BrokerRawTransaction`
- **THEN** the parser SHALL NOT append a warning for that transaction

### Requirement: Real Schwab Export Regression
The `SchwabJSONParser` SHALL import real Schwab exports produced by `schwab_cli.py` (and the Schwab Transactions API) — where equity legs carry no `instruction` field and fees are separate `CURRENCY` legs — without emitting per-transaction skip warnings.

#### Scenario: Real CLI export imports without warnings
- **WHEN** a real Schwab transactions export (equity legs with `positionEffect` + signed `amount`, integer `activityId`, `CURRENCY` fee legs) is parsed via `SchwabJSONParser.parse_raw()`
- **THEN** the parser SHALL create one `BrokerRawTransaction` per TRADE transaction and SHALL NOT append any "unknown instruction" or "could not parse" warning

#### Scenario: Integer activityId normalized to string
- **WHEN** a transaction has an integer `activityId` (e.g. `124780687237`)
- **THEN** the parser SHALL set the raw record `id = "schwab:124780687237"` (string form, no decimal suffix)
