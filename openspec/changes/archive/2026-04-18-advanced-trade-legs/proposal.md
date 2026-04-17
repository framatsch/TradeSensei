## Why

Traders often scale into or out of positions across multiple executions (legs). The current "Basic" trade creation form only allows specifying a single entry and a single exit price. To properly journal trades with multiple tranches, users need the ability to manually enter individual execution legs for a single trade. This implementation employs a "Progressive Disclosure" UX approach to keep the default form simple while providing advanced capabilities when needed.

## What Changes

- Add an "Advanced" mode toggle to the "New Trade" form.
- In Advanced mode, the main trade entry/exit price and quantity fields become read-only and automatically calculate their values based on the entered legs.
- Add a dynamic list of execution legs in the form, allowing users to add, edit, or remove individual execution legs (Date/Time, Side, Quantity, Price, Fees).
- Update the `TradeCreateRequest` backend schema to accept an optional list of `executions`.
- Update the `TradeService.create_trade` backend logic to skip auto-generation of legs and instead save the provided executions when they are present.
- Migrate the Frontend `TradeForm` to use `react-hook-form` and `useFieldArray` for robust dynamic list state management.

## Capabilities

### New Capabilities
- `advanced-trade-legs`: Allows users to manually add multiple execution legs when creating a new trade.

### Modified Capabilities
- `trade-creation`: The API and UI requirements for creating a trade are expanded to support an optional array of manual executions instead of just relying on top-level entry/exit prices.

## Impact

- **Frontend**: The `TradeForm.tsx` component will be heavily refactored to use `react-hook-form`.
- **Backend API**: The `POST /trades` endpoint payload (`TradeCreateRequest`) will be expanded in a backward-compatible way.
- **Backend Logic**: The `TradeService` will need to handle the new `executions` payload.
- **Database**: No schema changes required (the `LogicalExecution` model already exists and is linked to trades).