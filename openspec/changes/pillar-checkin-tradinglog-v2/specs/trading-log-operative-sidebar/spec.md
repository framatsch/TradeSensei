## Delta Spec (Modification)

This spec revises the existing `trading-log-operative-sidebar` capability. Only requirements that CHANGE are listed here. Unchanged requirements from the archived spec remain in force.

## UI Mockup (revised)

```
+---------------------------------------------------------------------------------+
| [ 🍱 ] > TRADING LOG                                 Portfolio: [ Default ▼ ]   |
+----------------------+----------------------------------------------------------+
| -- ACTIONS --        |  [ ▼ Filter Configuration ]                              |
| [+ ] New Trade       |  (Search, Date, Status, etc.)             [ Save Filter ]|
| [📥] Quick Import    |                                                          |
| [📤] CSV Export      |  +------------+-------+-------+----------+---------+     |
|                      |  | Date       | Asset | Setup | P&L ($)  | P&L (R) |     |
| -- SAVED FILTERS --  |  +------------+-------+-------+----------+---------+     |
| [📝] All Trades      |  | 03.05.2026 | AAPL  | Break | +$450.00 | +2.5 R  |     |
|    • Open Trades     |  | 02.05.2026 | TSLA  | Trend | -$150.00 | -1.0 R  |     |
|    • All Winners     |  +------------+-------+-------+----------+---------+     |
|    • All Losers      |                                                          |
|    • Custom Setup A  |  < 1 2 3 ... 10 >          [ Rows per page: 50 ▼ ]       |
+----------------------+----------------------------------------------------------+
```

**Changes from previous version:**
- Sidebar second section label is **"SAVED FILTERS"** (was "Trades").
- Column Visibility Toggle is **explicitly prohibited** — must not appear anywhere in the Trading Log table.

## Changed Requirements

### Requirement CHANGED: Sidebar "Saved Filters" section label is "SAVED FILTERS"
The sidebar section that lists filter shortcuts SHALL be labeled "SAVED FILTERS" (all caps, matching mockup). The previous label "Trades" is incorrect and must not be used.

#### Scenario: Sidebar shows "SAVED FILTERS" section heading
- **WHEN** the user views the Trading Log sidebar
- **THEN** the filter shortcuts section is headed "SAVED FILTERS"
- **AND** the section contains: All Trades, Open Trades, All Winners, All Losers, and any user-saved filters

### Requirement ADDED: Column Visibility Toggle is prohibited
A Column Visibility Toggle control SHALL NOT appear anywhere in the Trading Log table or its surrounding UI. If such a control was implemented, it must be removed.

#### Scenario: No column visibility toggle exists
- **WHEN** the user views the Trading Log table
- **THEN** there is no button, dropdown, or menu that allows toggling column visibility
