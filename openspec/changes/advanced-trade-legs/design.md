## Context

The current `TradeForm` component uses simple `useState` hooks for each field (symbol, direction, entry price, etc.). It creates a single flat `TradeCreateRequest` payload. To support adding multiple execution legs (a dynamic array of objects), the form state management needs to be upgraded. `react-hook-form` with `useFieldArray` is the industry standard for this pattern in React.

On the backend, `TradeService.create_trade` currently auto-generates 1 or 2 `LogicalExecution` legs based on the `entry_price` and `exit_price` provided. It needs to accept a list of executions instead and skip the auto-generation when this list is provided.

## Goals / Non-Goals

**Goals:**
- Allow users to enter multiple execution legs for a single trade.
- Keep the default form simple (Progressive Disclosure) by hiding the legs behind an "Advanced" toggle.
- Automatically calculate total quantity and average entry/exit prices from the entered legs to keep the top-level trade data consistent.
- Refactor the `TradeForm` to use `react-hook-form`.

**Non-Goals:**
- We are not building a fully automated trade import pipeline here; this is strictly for manual trade entry via the UI.
- We are not changing the database schema (`LogicalExecution` already exists and supports multiple legs per trade).

## Decisions

**1. Form State Management**
*Decision*: Migrate `TradeForm` to `react-hook-form` using `useFieldArray`.
*Rationale*: Managing dynamic arrays of inputs with pure `useState` is error-prone, verbose, and performs poorly (re-renders the whole form on every keystroke). `react-hook-form` handles this elegantly and integrates well with our existing UI components.

**2. Backend API Contract**
*Decision*: Add `executions: list[ExecutionCreateRequest] | None = None` to `TradeCreateRequest`.
*Rationale*: This is a non-breaking change. Existing clients (or the Basic mode of the form) that don't send `executions` will continue to trigger the auto-generation logic. Clients that send `executions` will explicitly define the legs.

**3. Auto-Aggregation in Frontend**
*Decision*: Calculate top-level trade fields (quantity, entry_price, exit_price, opened_at, closed_at) automatically from the legs in Advanced mode, and make those top-level inputs read-only.
*Rationale*: The backend expects valid top-level trade metrics. By calculating them on the fly in the frontend, the user gets immediate visual feedback, and the backend doesn't have to guess or override the top-level metrics. We ensure Single Source of Truth consistency.

## Risks / Trade-offs

- **Risk**: Refactoring the entire `TradeForm` to `react-hook-form` might introduce regressions in the existing "Basic" mode.
  - *Mitigation*: We will carefully map all existing fields and ensure the validation logic remains identical. We will test the Basic mode thoroughly before merging.
- **Risk**: The user might enter conflicting legs (e.g., closing more quantity than was opened).
  - *Mitigation*: We will rely on the existing backend validation rules that check if a trade's legs sum up correctly. Long term, we can add frontend validation.