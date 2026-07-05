> Depends on `open-position-seeding`. Do not add origin/constraint/flag/service tasks here — consume them from the contract.

## 1. Parser — OpenPosition ingestion (IBKR adapter)

- [ ] 1.1 Add `_parse_open_position_element_raw()` to `IBKRXMLParser` in `backend/app/utils/parsers/ibkr_xml.py` that converts an `<OpenPosition>` element to a `BrokerRawTransactionCreate`.
- [ ] 1.2 Set `is_open_position = True` (contract flag); set `id = "ibkr:{transactionID}"` with the deterministic composite fallback `ibkr:{symbol}:{yyyymmddHHMMSS}:{quantity}` when `transactionID` is absent.
- [ ] 1.3 Set `executed_at` from `openDate` (UTC); compute `price = abs(costBasis) / (abs(position) * multiplier)`. Do not set `origin`/`pnl` (shared layer handles those).
- [ ] 1.4 Skip `assetCategory = "CASH"` silently; skip missing-`symbol` with a warning appended to `IBKRXMLParser.warnings`.
- [ ] 1.5 Call `_parse_open_position_element_raw()` in `parse_raw()` after `<Trade>`/`<Execution>` processing (`root.findall(".//OpenPosition")`).

## 2. Unit tests — parser

- [ ] 2.1 Minimal Flex XML with `<OpenPosition>` elements → assert emitted `BrokerRawTransactionCreate` records (symbol, direction, quantity, price, `executed_at`, `is_open_position=True`, `id` format). Note: `conid` is populated from IBKR (unlike Schwab), so the aggregator's `(symbol, conid, asset_class)` key uses the real conid.
- [ ] 2.2 Composite-key fallback when `transactionID` is absent.
- [ ] 2.3 CASH `<OpenPosition>` skipped silently.
- [ ] 2.4 Missing-`symbol` `<OpenPosition>` appends a warning and is skipped.

## 3. Integration tests — full IBKR cycle (via contract)

- [ ] 3.1 Full Flex XML import (`ImportService.import_file`) with both `<OpenPosition>` and `<Trade>` elements → the open position creates an open-lot `Trade`; a later closing `<Trade>` closes it (both `opened_at`/`closed_at`).
- [ ] 3.2 Import the same XML twice → no duplicate `BrokerRawTransaction`/`LogicalExecution` (exact reconciliation via shared `ibkr:{transactionID}`).
- [ ] 3.3 Snapshot open + later real opening `<Trade>` with the same `transactionID` → exactly one open lot (collapses via upsert; does not reach the contract's no-shared-id guard).

## 4. Verification

- [ ] 4.1 `lint-check` (ruff + `mypy --strict`) — zero new errors.
- [ ] 4.2 `unit-test` (pytest) for IBKR parser + integration cycle — green (contract change must be present).
