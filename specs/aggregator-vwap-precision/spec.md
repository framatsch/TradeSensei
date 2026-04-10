# Aggregator VWAP Precision Specification

## Overview

This specification defines the precise VWAP (Volume-Weighted Average Price) calculation requirements for the FIFO execution aggregator when consolidating multiple execution legs into a single trade record.

## Scenario 1: Multi-Leg Entry with Single Exit (Multiplier=1)

### Input Executions

| Leg | Direction | Quantity | Price  | Commission | Executed At         |
|-----|-----------|----------|--------|------------|---------------------|
| 1   | BUY       | 100      | 373.62 | 5.00       | 2025-01-10 10:00 UTC|
| 2   | BUY       | 50       | 375.00 | 2.50       | 2025-01-10 11:00 UTC|
| 3   | SELL      | 150      | 377.96 | 7.50       | 2025-01-10 12:00 UTC|

### Calculations

**Entry Price (VWAP)**
```
VWAP_entry = (100 * 373.62 + 50 * 375.00) / 150
           = (37362 + 18750) / 150
           = 56112 / 150
           = 374.08
```

**Exit Price (VWAP)**
```
VWAP_exit = 377.96 (single exit leg)
```

**Gross P&L**
```
gross_pnl = (exit_price - entry_price) * quantity * multiplier
          = (377.96 - 374.08) * 150 * 1
          = 3.88 * 150
          = 582.00
```

**Commission Total**
```
commission_total = 5.00 + 2.50 + 7.50 = 15.00
```

**Net P&L**
```
net_pnl = gross_pnl - commission_total
        = 582.00 - 15.00
        = 567.00
```

**Timestamps**
```
opened_at = 2025-01-10 10:00 UTC (first entry leg)
closed_at = 2025-01-10 12:00 UTC (last exit leg)
```

### Expected Trade Fields

| Field              | Value         |
|--------------------|---------------|
| quantity           | 150           |
| entry_price        | 374.08        |
| exit_price         | 377.96        |
| pnl                | 582.00        |
| net_pnl            | 567.00        |
| commission         | 15.00         |
| opened_at          | 2025-01-10 10:00 UTC |
| closed_at          | 2025-01-10 12:00 UTC |

---

## Scenario 2: Options Contract with Multiplier=100

### Input Executions

| Leg | Direction | Quantity | Price | Commission | Executed At         | Multiplier |
|-----|-----------|----------|-------|------------|---------------------|------------|
| 1   | BUY       | 10       | 5.50  | 10.00      | 2025-01-15 09:30 UTC| 100        |
| 2   | SELL      | 6        | 5.75  | 6.00       | 2025-01-15 11:00 UTC| 100        |
| 3   | SELL      | 4        | 5.80  | 4.00       | 2025-01-15 14:00 UTC| 100        |

### Calculations

**Entry Price (VWAP)**
```
VWAP_entry = (10 * 5.50) / 10 = 5.50
```

**Partial Exit Matching (FIFO)**

First exit leg (6 contracts @ 5.75):
```
matched_pnl_1 = (5.75 - 5.50) * 6 = 0.25 * 6 = 1.50
```

Second exit leg (4 contracts @ 5.80):
```
matched_pnl_2 = (5.80 - 5.50) * 4 = 0.30 * 4 = 1.20
```

**Gross P&L (Sum of Matched Legs)**
```
gross_pnl = matched_pnl_1 + matched_pnl_2
          = 1.50 + 1.20
          = 2.70
```

**Commission Total**
```
commission_total = 10.00 + 6.00 + 4.00 = 20.00
```

**Net P&L**
```
net_pnl = gross_pnl - commission_total
        = 2.70 - 20.00
        = -17.30
```

**Timestamps**
```
opened_at = 2025-01-15 09:30 UTC (first entry leg)
closed_at = 2025-01-15 14:00 UTC (last exit leg)
```

### Expected Trade Fields

| Field              | Value         |
|--------------------|---------------|
| quantity           | 10            |
| entry_price        | 5.50          |
| exit_price         | 5.77 (VWAP of exits) |
| pnl                | 2.70          |
| net_pnl            | -17.30        |
| commission         | 20.00         |
| opened_at          | 2025-01-15 09:30 UTC |
| closed_at          | 2025-01-15 14:00 UTC |

---

## Precision Requirements

1. **Decimal Precision**: All monetary values must use `Decimal` type with at least 2 decimal places.
2. **Rounding**: Round to 2 decimal places for final assertions (use `round(value, 2)`).
3. **VWAP Calculation**: Use exact arithmetic (no floating-point approximations).
4. **Partial Closes**: Match exit legs to entry lots in FIFO order; compute P&L per matched pair.

## Test Implementation

Tests must verify:
- Entry price (VWAP) calculation correctness
- Exit price (VWAP) calculation correctness
- Gross P&L computation
- Net P&L computation (gross P&L - commission)
- Commission aggregation
- Timestamp assignment (opened_at from first entry, closed_at from last exit)
- All values use `Decimal` type (no float comparisons)
