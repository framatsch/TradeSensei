## Why

Currently, the trading journal only tracks actual trades (buy/sell actions) and their resulting Profit and Loss (PnL). However, cash flows like dividends, taxes (e.g. withholding tax), broker interest, and deposits/withdrawals are critical components for a comprehensive understanding of portfolio performance and for tax reporting. By introducing cash transactions, users will be able to accurately reflect their total return, generate proper tax reports at year-end, and perfectly reconcile their account's cash balance. 

## What Changes

- Add a new data model to track various types of cash transactions: DIVIDEND, WITHHOLDING_TAX, DEPOSIT, WITHDRAWAL, INTEREST, and FEE.
- Extend existing data import parsers (IBKR XML and Schwab CSV) to extract and persist cash transaction events.
- Enhance the API to provide CRUD, filtering, and paging endpoints for cash transactions.
- Extend the frontend with a new "Cash & Dividends" page, offering list views (with filtering and pagination), CRUD capabilities, and summary widgets.
- Adjust account performance metrics to optionally include dividends and net cash flows to reflect the True Total Return.

## Capabilities

### New Capabilities
- `cash-transactions`: CRUD operations for cash transactions (dividends, taxes, interest, deposits/withdrawals).
- `cash-transactions-ui`: A dedicated page in the frontend to list, filter, paginate, and manage cash transactions.
- `cash-transactions-import`: Extended broker import support to parse and persist non-trade cash entries.
- `account-metrics`: Account performance calculations will be updated to optionally aggregate cash transactions (e.g., dividends) for a True Total Return view.

### Modified Capabilities

## Impact

- **Backend / Database**: New `CashTransaction` SQLAlchemy model and corresponding Alembic migration.
- **Backend / API**: New `/api/cash-transactions` endpoints; modifications to `/api/accounts/{id}/metrics` to include cash flow aggregations.
- **Backend / Parsers**: Modifications to `IBKRParser` and `SchwabParser`.
- **Frontend**: New `CashTransactions` page component, route, and API client hooks. Adjustments to Dashboard and Account views for cash summaries.