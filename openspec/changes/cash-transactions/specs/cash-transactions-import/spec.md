## ADDED Requirements

### Requirement: Import cash transactions from broker files
The system SHALL extract cash transactions (dividends, taxes, interest, deposits) during broker file imports (IBKR XML and Schwab CSV) and persist them alongside trades.

#### Scenario: Import IBKR dividends and taxes
- **WHEN** an IBKR Flex Query XML containing `<CashTransaction>` elements is uploaded
- **THEN** the parser creates `CashTransaction` records mapping correctly to DIVIDEND, WITHHOLDING_TAX, INTEREST, or FEE types

#### Scenario: Import Schwab dividends
- **WHEN** a Schwab CSV containing rows with action "Dividend" or "Tax Withholding" is uploaded
- **THEN** the parser creates corresponding `CashTransaction` records instead of skipping those rows

#### Scenario: Import IBKR currency conversions (Forex)
- **WHEN** an IBKR `<Trade>` node has `assetCategory="CASH"` (e.g. converting EUR to USD)
- **THEN** the parser skips importing it as a regular trade but creates a `FEE` `CashTransaction` for any commission incurred during the exchange.

#### Scenario: Prevent duplicates during re-import
- **WHEN** a user re-imports a file containing previously imported cash transactions
- **THEN** the system ignores the exact duplicates (based on date, type, symbol, and amount) or replaces them appropriately