## ADDED Requirements

### Requirement: Generic files import only into GENERIC accounts
The `generic` adapter SHALL be registered for `AccountType.GENERIC` with file-import capability only (extensions `json`, `csv`), no remote sync, no connection capability and no account binding. Generic imports SHALL terminate in `ImportService.import_trades()`.

#### Scenario: Upload to GENERIC account
- **WHEN** a valid generic JSON file is uploaded via `POST /portfolios/{portfolio_id}/imports/upload` for a `GENERIC` account
- **THEN** the executions SHALL be imported through the standard pipeline and an `ImportResult` returned

#### Scenario: Generic file to IBKR account
- **WHEN** a `.csv` file is uploaded for an `IBKR` account
- **THEN** the request SHALL be rejected with HTTP 422

#### Scenario: Sync on GENERIC account
- **WHEN** a sync is requested for a `GENERIC` account
- **THEN** the request SHALL be rejected as unsupported and nothing SHALL be written

### Requirement: Mapping to canonical raw executions
The adapter SHALL map each execution to a canonical raw execution: `side` `BUY`→`LONG`, `SELL`→`SHORT`; `position_effect` `OPEN`→`open_close='O'`, `CLOSE`→`'C'`, `CLOSE_OPEN`→ same representation as an IBKR mixed execution with `is_mixed_execution=true`, absent→`None`; `option.*`→`strike`/`expiry`/`option_type`; `realized_pnl`→`pnl`; `order_id`→`order_id`. `conid` SHALL be `contract_id` when provided, otherwise for options a deterministic key `"{symbol}:{expiry:%Y%m%d}:{right}:{strike normalized}"`, otherwise `NULL`. When `order_id` is present, `net_cash` SHALL be derived with the same sign convention as IBKR `netCash`. The original row SHALL be stored in `raw_data`.

#### Scenario: Two option contracts on the same underlying stay separate
- **WHEN** a file contains SPY 580C and SPY 590C executions without `contract_id`
- **THEN** they SHALL receive different `conid` values and SHALL NOT be FIFO-matched against each other

#### Scenario: Position flip
- **WHEN** an execution has `position_effect: "CLOSE_OPEN"`
- **THEN** the resulting logical execution SHALL have `is_mixed_execution=true` and aggregate exactly like an IBKR `C;O` execution

#### Scenario: Equivalence with native IBKR import
- **WHEN** each IBKR test fixture is converted to the generic format (preserving `transactionID`→`external_id`, `brokerageOrderID`→`order_id`, `conid`→`contract_id`, open/close indicator, splits) and imported into a fresh `GENERIC` account
- **THEN** the resulting trades (symbols, directions, quantities, prices, commissions, P&L, open/closed state, combo grouping) SHALL equal those of the native IBKR import of the same fixture

### Requirement: Account-scoped raw identity
Raw transaction IDs for generic imports SHALL be `{user_id}:generic:{account_id}:x:{external_id}` in external-ID mode and `{user_id}:generic:{account_id}:f:{fingerprint}:{ordinal}` in fingerprint mode, so identical IDs in different `GENERIC` accounts of the same user never collide.

#### Scenario: Same external_id in two accounts
- **WHEN** a user imports an execution with `external_id: "1001"` into GENERIC account A and a different execution with `external_id: "1001"` into GENERIC account B
- **THEN** both executions SHALL be persisted

### Requirement: Fingerprint mode for files without IDs
When executions carry no `external_id`, the fingerprint SHALL be the SHA-256 of a canonical string of: `executed_at` in UTC (ISO 8601, microsecond precision), `symbol`, `asset_class`, `conid` as derived above, `side`, normalized `quantity`, normalized `price`, `currency`. The ordinal SHALL be the 1-based occurrence index of that fingerprint within the file in file order. Commission, `position_effect`, `order_id` and `realized_pnl` SHALL NOT be part of the fingerprint.

#### Scenario: Re-import of the same file
- **WHEN** the same ID-less file is imported twice
- **THEN** the second import SHALL insert zero raw transactions

#### Scenario: Overlapping export windows
- **WHEN** a file covering January–March and later a file covering March–May are imported, both containing the identical March executions
- **THEN** the March executions SHALL exist exactly once

#### Scenario: Identical partial fills
- **WHEN** a file contains two fills with identical time, contract, side, quantity and price
- **THEN** both SHALL be imported as distinct raw transactions (ordinals 1 and 2)

### Requirement: ID strategy is fixed per account
The first non-dry-run generic import into an account SHALL record the account's ID strategy (`external_id` or `fingerprint`) as an account property. Subsequent imports with the other strategy SHALL be rejected with HTTP 422 and an explanatory message. Clearing all trades of the account (Danger Zone) SHALL reset the recorded strategy.

#### Scenario: Switching strategy rejected
- **WHEN** an account was first imported in fingerprint mode and a file with `external_id` values is uploaded
- **THEN** the import SHALL be rejected with error code `id_strategy_mismatch` and nothing SHALL be written

#### Scenario: Reset via clear-all-trades
- **WHEN** the user clears all trades of the account and then uploads a file with `external_id` values
- **THEN** the import SHALL succeed and record `external_id` as the strategy

### Requirement: Dry-run preview
`POST /api/v1/portfolios/{portfolio_id}/imports/preview` (same multipart form as `/upload`) SHALL validate the file and compute raw IDs without writing anything, returning: detected ID strategy, account's recorded strategy (or null), whether they conflict, total executions, new executions, already-imported executions, suppressed executions, new splits, conflicting splits, warnings and validation errors. The preview SHALL be available for `GENERIC` accounts.

#### Scenario: Preview writes nothing
- **WHEN** a preview is requested for a valid file
- **THEN** no raw transactions, logical executions, trades, corporate actions or account properties SHALL be created or modified

#### Scenario: Preview reports known executions
- **WHEN** a file is previewed whose executions were all imported before
- **THEN** `new` SHALL be 0 and `already_imported` SHALL equal `total`

#### Scenario: Preview surfaces validation errors
- **WHEN** an invalid file is previewed
- **THEN** the response SHALL contain the row-level errors defined by the format spec and HTTP 422

### Requirement: Splits from generic files are insert-only
For each split in a generic file: if no split exists for the user, symbol and date, it SHALL be created; if one exists with the same ratio, nothing changes; if one exists with a different ratio, it SHALL NOT be modified and a warning SHALL be added to the result and preview.

#### Scenario: Conflicting split ratio
- **WHEN** an IBKR import created a 1:10 split for XYZ on 2026-05-01 and a generic file declares ratio 0.2 for XYZ on 2026-05-01
- **THEN** the stored ratio SHALL remain 0.1 and the import result SHALL contain a split-conflict warning

### Requirement: Generic import UI
The import dialog SHALL, for `GENERIC` accounts, accept `.json` and `.csv` files, show a link to the format help section and a CSV template download, run the preview first and display its counts and errors, and import only after explicit user confirmation. The account create modal SHALL offer the `GENERIC` type labelled "Other broker (generic file)".

#### Scenario: Preview then confirm
- **WHEN** the user selects a valid file for a `GENERIC` account
- **THEN** the dialog SHALL display new / already-imported counts and the ID strategy and SHALL import only after the user confirms

#### Scenario: Strategy conflict shown before import
- **WHEN** the preview reports an ID strategy conflict
- **THEN** the confirm action SHALL be disabled and the message SHALL explain how to resolve it

### Requirement: Audit logging for generic imports
Generic imports SHALL emit the same audit events as other file imports (middleware for `/upload` and `/preview`, plus the existing manual import event with counts only). The ID strategy lock SHALL emit `account.import_strategy_set` with `account_id` and strategy only.

#### Scenario: Strategy lock audited
- **WHEN** the first generic import records the ID strategy
- **THEN** an `account.import_strategy_set` event SHALL be emitted without prices, quantities, symbols or P&L
