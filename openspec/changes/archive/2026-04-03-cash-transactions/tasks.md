## 1. Data Model and Database

- [x] 1.1 Add `CashTransactionType` string enum (DIVIDEND, WITHHOLDING_TAX, DEPOSIT, WITHDRAWAL, INTEREST, FEE, OTHER) to `backend/app/models/enums.py`
- [x] 1.2 Create `CashTransaction` SQLAlchemy model in `backend/app/models/cash_transaction.py` with columns for id, account_id, date, type, symbol (optional), amount, currency, amount_eur, and description.
- [x] 1.3 Add a bidirectional relationship between `Account` and `CashTransaction`.
- [x] 1.4 Generate Alembic migration for the `cash_transactions` table.
- [x] 1.5 Create Pydantic schemas (Create, Read, Update) for `CashTransaction` in `backend/app/schemas/cash_transaction.py`.

## 2. API and Repository Layer

- [x] 2.1 Create `CashTransactionRepository` for basic CRUD and listing filtered by `account_id` and `type` with pagination.
- [x] 2.2 Create `CashTransactionService` to orchestrate operations (including checking FxRateService for `amount_eur` if missing).
- [x] 2.3 Create `backend/app/api/v1/cash_transactions.py` with routes for `GET`, `POST`, `PUT`, `DELETE`.
- [x] 2.4 Register the router in `backend/app/main.py`.
- [x] 2.5 Update the openapi.json and frontend TS client (`openapi-sync`).

## 3. Account Metrics Integration

- [x] 3.1 Update `AccountRepository.get_metrics` (or `AccountService`) to calculate `total_dividends` and `total_withholding_tax`.
- [x] 3.2 Update `AccountMetrics` schema to include the new fields.
- [x] 3.3 Ensure the dashboard API endpoints optionally incorporate these into a "Total Return".

## 4. Import Parsers Update

- [x] 4.1 Update `IBKRParser` in `backend/app/utils/parsers/ibkr.py` to process `<CashTransaction>` blocks (map type, handle fx conversion). Also, filter out `<Trade assetCategory="CASH">` from trades, and extract their commission into `FEE` cash transactions.
- [x] 4.2 Update `SchwabParser` in `backend/app/utils/parsers/schwab.py` to process "Dividend", "Tax Withholding", etc.
- [x] 4.3 Update `ImportService` to persist both `Trade` and `CashTransaction` records returned by parsers.
- [x] 4.4 Add unit tests for cash transaction parsing in `tests/test_import.py`.

## 5. Frontend Development

- [x] 5.1 Create `CashTransactions` page at `frontend/app/dashboard/cash/page.tsx`.
- [x] 5.2 Implement a data table with columns for date, type, symbol, amount, and currency.
- [x] 5.3 Implement filtering by `type` and pagination controls.
- [x] 5.4 Implement "Add Manual Cash Transaction" modal dialog.
- [x] 5.5 Implement "Delete" and "Edit" action buttons in the data table.
- [x] 5.6 Add Summary Widgets (Total Flow, Total Dividends, Total Tax) at the top of the page.
- [x] 5.7 Update dashboard sidebar navigation to include "Cash & Dividends" link.