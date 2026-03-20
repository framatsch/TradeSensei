## Context

The current trade journaling system is focused purely on tracking filled trades and their direct profit/loss. This creates an incomplete picture of an account's financial health, as dividends, withholding taxes, broker fees, and interest make up a significant portion of an investor's total return and cash balance over time. Adding tracking for these cash flow events is essential for tax reporting, accurate total performance calculations, and exact cash balance reconciliation.

## Goals / Non-Goals

**Goals:**
- Provide a robust persistence layer (`CashTransaction` model) for all non-trade cash flows.
- Seamlessly import `CashTransaction` data from standard IBKR (Flex Query XML) and Schwab (CSV) reports alongside standard trade operations.
- Provide full API support (CRUD, pagination, filtering) for the new resource.
- Display a dedicated UI in the frontend allowing users to manage, filter, and view summaries of their cash transactions.
- Keep the design generic enough (using an extensible `type` enum) so future transaction types can be added easily.

**Non-Goals:**
- Full tax calculation engine (we will record the raw transaction amounts and let the user do external calculations if needed, though simple aggregations will be provided).
- Complex multi-currency conversion at the exact historical daily rate for every minor fee. (We will use the same EUR/USD daily fallback logic as we currently use for trades).
- Replacing the existing `Trade` model with a generalized ledger system. We will maintain `Trade` and `CashTransaction` as separate but related entities, connected via the `Account` model.

## Decisions

- **Data Model Separation**: We decided to introduce a new `CashTransaction` model rather than trying to fit these events into the existing `Trade` model. A dividend payout doesn't have an entry/exit price, direction, or duration. Maintaining separate models preserves the tight validation schema on `Trade` while allowing `CashTransaction` to stay lightweight and specific.
- **Enum for Transaction Types**: We will use a `CashTransactionType` string enum (e.g., `DIVIDEND`, `WITHHOLDING_TAX`, `DEPOSIT`, `WITHDRAWAL`, `INTEREST`, `FEE`, `OTHER`). This covers the known requirements while making filtering straightforward.
- **Optional Symbol Association**: Some cash transactions (like dividends or withholding tax) are directly tied to an asset symbol (e.g., MSFT). The `CashTransaction` model will have an optional `symbol` column to support filtering "Show me all MSFT dividends."
- **Import Strategy**: 
  - **IBKR**: Update the XML parser to read `<CashTransaction>` nodes (note: user needs to enable "Cash Transactions" in the Flex Query). Additionally, IBKR logs currency conversions (EUR to USD) as `<Trade assetCategory="CASH">`. These should be explicitly filtered out from the `Trade` list (as they are not real performance trades), but any commission incurred by them should be extracted and saved as a `FEE` `CashTransaction`.
  - **Schwab**: Update the CSV parser to handle the `Dividend`, `Tax Withholding`, `Deposit`, etc., actions instead of ignoring them.
- **EUR Conversion**: Apply the same `FxRateService` logic used in trades to calculate an `amount_eur` for accurate local tax reporting.

## Risks / Trade-offs

- **Risk: Backward compatibility for existing imports.** If a user imports a CSV/XML over an existing time period, do we risk duplicating cash transactions? 
  - *Mitigation*: We should implement an idempotent import strategy or add a unique constraint (e.g., `account_id`, `date`, `type`, `amount`, `symbol`) if possible, or advise users that re-importing the same files may result in duplicates just like trades.
- **Risk: Parser fragility.** Broker export formats for cash events might be less standardized than trades.
  - *Mitigation*: Keep parsers robust; gracefully skip unknown transaction types or map them to `OTHER` with a warning, rather than failing the whole import.
- **Trade-off: Simple vs. Double-entry Ledger.** We are using a simple list of transactions rather than a strict double-entry ledger. This is much easier to implement and fits the scope of a personal journal, but it lacks the strict mathematical guarantees of double-entry accounting.