# OpenSpec: Partial Trade Close (Split Execution)

## 1. Problem Statement
Users recording trades manually often enter a single "Open" position (e.g., 20 shares). When they exit this position in stages (e.g., selling 5 shares, then 15 shares), the current UI requires them to manually calculate quantities, duplicate notes/tags, and create new records. This is error-prone and tedious.

## 2. Proposed Solution
Add a "Partial Close" feature that automates the splitting of an open trade into two records:
1.  The **Remaining Open Trade**: Original record with reduced quantity.
2.  The **Closed Partial Trade**: A new record with the closed quantity, exit price, and a deep copy of all metadata.

## 3. Technical Requirements

### 3.1 Backend (FastAPI / SQLAlchemy)
- **Endpoint**: `POST /api/v1/trades/{trade_id}/partial-close`
- **Schema `TradePartialClose`**:
    - `quantity`: Decimal (Must be > 0 and < current trade quantity)
    - `exit_price`: Decimal
    - `closed_at`: datetime (UTC)
    - `exit_commission`: Decimal (Default 0)
- **Logic**:
    1.  Fetch original trade. Validate it is "Open" (`closed_at` is NULL).
    2.  Calculate proportional entry commission: `(original_commission * quantity_to_close) / original_quantity`.
    3.  **Update Original**: `original.quantity -= quantity_to_close`, `original.commission -= proportional_entry_commission`.
    4.  **Create New Trade**:
        - Copy all fields: `symbol`, `direction`, `asset_class`, `entry_price`, `opened_at`, `account_id`, `user_id`, `playbook_id`, `broker_conid`.
        - Set specific fields: `quantity = quantity_to_close`, `exit_price = input.exit_price`, `closed_at = input.closed_at`, `commission = proportional_entry_commission + input.exit_commission`.
        - **Deep Copy**: Duplicate all associated `Tag` entries and `TradeNote` entries.
    5.  Execute in a single DB transaction.

### 3.2 Frontend (Next.js / Tailwind)
- **UI Trigger**: "Partial Close" button in the Trade Actions menu (only for open trades).
- **Modal Component**: `PartialCloseModal`
    - Fields: Quantity (max = current), Exit Price, Close Date, Exit Commission.
    - Validation: Quantity cannot exceed current open quantity.
- **Workflow**: On success, refresh the trade list/detail view.

## 4. Edge Cases & Constraints
- **Full Close**: If user enters `quantity == current_quantity`, trigger a standard trade close instead of a split.
- **Manual Edits**: Once split, both trades are independent. Deleting one does not automatically "restore" the other (simplicity/stability over complexity).

## 5. Success Criteria
- User can split an open 20-share trade into a 15-share open trade and a 5-share closed trade with one click.
- Strategy, Playbook, and Tags are identical on both resulting records.
- P&L calculation remains accurate for both parts.
