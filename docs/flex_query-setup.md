# IBKR Flex Query Setup - Trade Sensei

**How to create and configure the IBKR Flex Query for trade imports**

**Version:** 2.0
**Date:** 2026-03-26
**Status:** Current

---

## Overview

Tradejournal provides a mechanism to sync your trade history with the platform.

## Prerequisites

1. **IBKR Account** with API access enabled
2. **API access credentials** to manage Flex Queries

---

## Step 1: Create Activity Flex Query in IBKR Client Portal

### Navigation

1. **Log in** to IBKR Client Portal (account.interactivebrokers.com)
2. Navigate to **Performance & Reports** (top navigation bar)
3. Select **Flex Queries**

### Create New Activity Query

In the **Activity Flex Query** section, click the **plus icon (+)**.

#### Query Configuration

| Setting | Value | Purpose |
|---------|-------|---------|
| **Query Name** | `TraderJournal` | Descriptive identifier |
| **Format** | XML | API-compatible format |
| **Period** | Last Business Day | Automatically covers previous trading day |
| **Frequency** | Daily | Runs once per business day |
| **Delivery Time** | After Market Close (~17:30 ET) | Ensures all trades are captured |

#### Data Sections (Select All fields)

✅ **Trades** - Trade executions
✅ **Positions** (or "Open Positions") - Current holdings
✅ **Cash Report** - Summary of cash flows, interest, and total balances
✅ **Cash Transactions** - Deposits, withdrawals, dividends
✅ **Corporate Actions** - Stock splits, mergers, and spin-offs
✅ **Open Positions** - Current holdings, cost basis, and unrealized P&L
✅ **Trades** - Detailed buy/sell executions and realized P&L
✅ **Transaction Fees** - Commission and fees
✅ **Cash Report** - Cash balance summary

#### Data Sections Explained

| Section | Purpose | For EOD Dashboard |
| ------- | ------- | ----------------- |
| **Trades** | Individual trade executions during the period | ✅ Required |
| **Positions** | Current open positions (holdings) | ✅ Required - shows active portfolio |
| **Cash Transactions** | Deposits, withdrawals, dividends, transfers | ✅ Optional - for cash tracking |
| **Transaction Fees** | Commission, fees, and charges | ✅ Optional - for cost analysis |
| **Cash Report** | Summary of cash balance by currency | ✅ Optional - for reporting |

**Note:**

- "Open Positions" and "Positions" are the same thing in IBKR - both show your current holdings.
- **Trades** includes both opening and closing trades. Each trade has an `openCloseIndicator` field:
  - `O` = Opening trade (creates new position)
  - `C` = Closing trade (reduces/closes position)
  - You don't need a separate "Closed Positions" section!

#### General Configuration

Apply these default settings:

| Setting | Value |
| ------- | ----- |
| Date Format | `yyyyMMdd` |
| Time Format | `HHmmss` |
| Date/Time Separator | `;` (semi-colon) |
| Profit and Loss | Default |
| Include Canceled Trades? | No |
| Include Currency Rates? | No |
| Include Audit Trail Fields? | No |
| Display Account Alias? | No |
| Breakout by Day? | No |

---

## Step 2: Enable Flex Web Service & Retrieve Query ID

### Enable API Access

1. Navigate to **Performance & Reports** → **Settings**
2. Select **Flex Web Service**
3. Set status to **On**
4. Copy the **Current Token** (keep this secret!)

### Find Your Query ID

1. Go back to **Flex Queries** overview page
2. Find your `Daily_EOD` query
3. Copy the **Query ID** (9+ digits)

**Example:**

```text
Query Name: TradeJournal
Query ID: 12341ds
```

---

## Step 3: Test Query Manually (IBKR Portal)

### Verify in IBKR

1. In **IBKR Client Portal**, navigate to **Reports** → **Flex Queries**
2. Click on your `TradeJournal` query
3. You should see trades fetched

---

## Reference

### Query ID Format

```
Query ID: Must be 9+ digits or alphanumeric
Example: 123456789, 987654321, 1A2B3C4D5E6F
```

### Flex Token Format

```
Token: alphanumeric string, ~50 characters
Example: abc123def456ghi789jkl012mno345pqr678stu
```

### Automation URL (For Reference)

Your Flex Query can be fetched via:

```
https://www.interactivebrokers.com/Universal/servlet/FlexStatementService.SendRequest?t=TOKEN&q=QUERY_ID&v=3
```

**Replace:**

- `TOKEN` → Your Flex Web Service token
- `QUERY_ID` → Your Query ID

Data is typically available daily after **22:00 UTC** (IBKR processes EOD data).

---

## IBKR Flex API Documentation

- [IBKR Flex Web Service Docs](https://www.interactivebrokers.com/en/software/apiguide/apiguide.htm)
- [Flex Query Reference](https://www.interactivebrokers.com/en/software/apiguide/apiguide.htm#gettingstarted/flex_web_service.htm)

---

## ⚠️ Limitations

- Exporting the XML file from the broker only allows 365 days at a time. If you are looking to export more than one year you must run one export per year.
- Interactive Broker creates DUST trades sometimes when trading currencies different from your base currencies. These trades are entered as open trades on TraderSync. You must close them manually creating an opposite order with the same price so they show as breakeven