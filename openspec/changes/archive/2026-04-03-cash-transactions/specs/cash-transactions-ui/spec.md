## ADDED Requirements

### Requirement: Dedicated cash transactions view
The frontend SHALL provide a dedicated view to list, filter, and manage cash transactions for an account.

#### Scenario: View transactions list
- **WHEN** the user navigates to the "Cash & Dividends" tab of their account
- **THEN** they see a table displaying the cash transactions with columns for date, type, symbol, amount, currency, and amount_eur

#### Scenario: Filter by transaction type
- **WHEN** the user selects "DIVIDEND" from the type filter dropdown
- **THEN** the table updates to show only dividend transactions

#### Scenario: Summarize cash transactions
- **WHEN** the user views the cash transactions page
- **THEN** summary widgets display the total net flow, total dividends, and total withholding tax for the selected period