## 1. Backend Adjustments

- [x] 1.1 Add `executions: list[ExecutionCreateRequest] | None = None` to `TradeCreateRequest` in `backend/app/schemas/trade.py`
- [x] 1.2 Update `TradeService.create_trade` in `backend/app/services/trade_service.py` to bypass auto-generation if `data.executions` is present
- [x] 1.3 Update `TradeService.create_trade` to iterate through `data.executions` and create `LogicalExecution` entries associated with the trade
- [x] 1.4 Add unit tests in `backend/tests/test_trade_service.py` to verify manual execution legs creation path

## 2. Frontend React Hook Form Setup

- [x] 2.1 Refactor `TradeForm.tsx` to use `react-hook-form` instead of raw `useState` for existing "Basic" mode inputs
- [x] 2.2 Ensure the form submission payload format remains identical in "Basic" mode
- [x] 2.3 Verify existing form validation logic works identically after migrating to `react-hook-form`

## 3. Frontend Advanced Mode Implementation

- [x] 3.1 Add a visual toggle switch "Advanced (Manual Legs)" to `TradeForm.tsx`
- [x] 3.2 Integrate `useFieldArray` to manage the dynamic list of execution legs when "Advanced" mode is active
- [x] 3.3 Create the UI for individual legs (Date, Side, Quantity, Price, Fees, Delete button) and an "Add Leg" button
- [x] 3.4 Change the main `quantity`, `entry_price`, and `exit_price` fields to be read-only inputs when "Advanced" mode is enabled
- [x] 3.5 Add a `useEffect` (or `useWatch`) to automatically aggregate the values of the execution legs and update the main read-only trade fields

## 4. Final Integration

- [x] 4.1 Update the form submission logic to append the `executions` array when submitting in "Advanced" mode
- [x] 4.2 Perform an end-to-end manual test creating a trade in "Basic" mode
- [x] 4.3 Perform an end-to-end manual test creating a trade in "Advanced" mode with multiple legs

## 5. Automated E2E Testing (Playwright)

- [x] 5.1 Add Playwright test to verify successful trade creation in standard "Basic" mode.
- [x] 5.2 Add Playwright test to verify "Advanced" mode toggle makes main fields read-only and displays the dynamic legs list.
- [x] 5.3 Add Playwright test to verify adding legs auto-calculates total quantity and average entry/exit prices correctly.
- [x] 5.4 Add Playwright test to verify successful submission of an "Advanced" mode trade and rendering of multiple legs in the Trade Detail view.