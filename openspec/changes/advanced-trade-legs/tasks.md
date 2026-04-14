## 1. Backend Adjustments

- [ ] 1.1 Add `executions: list[ExecutionCreateRequest] | None = None` to `TradeCreateRequest` in `backend/app/schemas/trade.py`
- [ ] 1.2 Update `TradeService.create_trade` in `backend/app/services/trade_service.py` to bypass auto-generation if `data.executions` is present
- [ ] 1.3 Update `TradeService.create_trade` to iterate through `data.executions` and create `LogicalExecution` entries associated with the trade
- [ ] 1.4 Add unit tests in `backend/tests/test_trade_service.py` to verify manual execution legs creation path

## 2. Frontend React Hook Form Setup

- [ ] 2.1 Refactor `TradeForm.tsx` to use `react-hook-form` instead of raw `useState` for existing "Basic" mode inputs
- [ ] 2.2 Ensure the form submission payload format remains identical in "Basic" mode
- [ ] 2.3 Verify existing form validation logic works identically after migrating to `react-hook-form`

## 3. Frontend Advanced Mode Implementation

- [ ] 3.1 Add a visual toggle switch "Advanced (Manual Legs)" to `TradeForm.tsx`
- [ ] 3.2 Integrate `useFieldArray` to manage the dynamic list of execution legs when "Advanced" mode is active
- [ ] 3.3 Create the UI for individual legs (Date, Side, Quantity, Price, Fees, Delete button) and an "Add Leg" button
- [ ] 3.4 Change the main `quantity`, `entry_price`, and `exit_price` fields to be read-only inputs when "Advanced" mode is enabled
- [ ] 3.5 Add a `useEffect` (or `useWatch`) to automatically aggregate the values of the execution legs and update the main read-only trade fields

## 4. Final Integration

- [ ] 4.1 Update the form submission logic to append the `executions` array when submitting in "Advanced" mode
- [ ] 4.2 Perform an end-to-end manual test creating a trade in "Basic" mode
- [ ] 4.3 Perform an end-to-end manual test creating a trade in "Advanced" mode with multiple legs

## 5. Automated E2E Testing (Playwright)

- [ ] 5.1 Add Playwright test to verify successful trade creation in standard "Basic" mode.
- [ ] 5.2 Add Playwright test to verify "Advanced" mode toggle makes main fields read-only and displays the dynamic legs list.
- [ ] 5.3 Add Playwright test to verify adding legs auto-calculates total quantity and average entry/exit prices correctly.
- [ ] 5.4 Add Playwright test to verify successful submission of an "Advanced" mode trade and rendering of multiple legs in the Trade Detail view.