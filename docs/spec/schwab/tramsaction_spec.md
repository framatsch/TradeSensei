# Technical Specification: Schwab Developer API - Trade Import (2026)

This document provides the definitive JSON schema and endpoint structure for the Charles Schwab Individual Trader API. It is designed to facilitate the mapping of transaction data into TradeSensei, with a specific focus on equities, options, and complex multi-leg (combo) strategies.

**Reference Files:**
- Fully extracted and inlined schema: [docs/spec/schwab/Transaction.json](docs/spec/schwab/Transaction.json)
- Original OpenAPI specification: [docs/spec/schwab/TraderApi-Prod_05-11-2024.json](docs/spec/schwab/TraderApi-Prod_05-11-2024.json)

---

## 1. API Architecture & Authentication

Data is retrieved via the Individual Trader API suite.

- **Endpoint:** `GET https://api.schwabapi.com/trader/v1/accounts/{accountHash}/transactions`
- **Authentication:** OAuth 2.0 (Authorization Code Grant)
- **Required Scopes:** `readonly`, `trader` (depending on app registration)

**Headers:**
```http
Authorization: Bearer {access_token}
Accept: application/json
```

---

## 2. Request Parameters

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `types` | string | Filter for activity types. Set to `TRADE` for execution data. |
| `startDate` | string | ISO-8601 (e.g., `2026-01-01T00:00:00.000Z`). Max 60-day window. |
| `endDate` | string | ISO-8601 end date. |
| `symbol` | string | Optional ticker filter. |

---

## 3. Transaction Schema Overview

Based on the extracted [Transaction.json](docs/spec/schwab/Transaction.json), a `Transaction` object contains the following core fields:

- **`activityId`** *(integer/int64)*: Unique ID of the activity.
- **`time`** *(string/date-time)*: Timestamp of the activity (UTC, ISO-8601).
- **`user`** *(object)*: Details of the acting user (inline object with `userId`, `login`, `type`, etc.).
- **`description`** *(string)*: Free-text description of the transaction.
- **`accountNumber`** *(string)*: Encrypted account ID.
- **`type`** *(enum)*: Base transaction type (e.g., `TRADE`, `DIVIDEND_OR_INTEREST`, `WIRE_IN`).
- **`status`** *(enum)*: E.g., `VALID`, `INVALID`, `PENDING`, `UNKNOWN`.
- **`subAccount`** *(enum)*: Sub-account type (`CASH`, `MARGIN`, `SHORT`, `DIV`, `INCOME`).
- **`tradeDate` / `settlementDate`** *(string/date-time)*: ISO-8601 execution and settlement dates.
- **`positionId` / `orderId`** *(integer/int64)*: Identifiers linking to positions and orders.
- **`netAmount`** *(number/double)*: Cash impact of the transaction.
- **`activityType`** *(enum)*: Specific activity subtype (e.g., `EXECUTION`, `TRANSFER`).

### `transferItems` (Inline Structure)

Each execution or transfer includes `transferItems` detailing the assets involved:

- **`instrument`**: Complex object defining the security. Includes `assetType` (`EQUITY`, `OPTION`, `INDEX`, etc.), `symbol`, `cusip` and specific subtypes (e.g., expiration dates and strike prices for options).
- **`amount`**, **`cost`**, **`price`** *(number/double)*: Quantity and monetary figures.
- **`feeType`** *(enum)*: Specific fee types (`COMMISSION`, `SEC_FEE`, etc.).
- **`positionEffect`** *(enum)*: `OPENING`, `CLOSING`, `AUTOMATIC`.

---

## 4. Payloads & Examples

### 4.1. Single Trade (Equity)

Each transaction represents a completed execution. The `transferItems` array contains the asset details.

```json
{
  "activityId": 9081273456,
  "orderId": 55443322,
  "type": "TRADE",
  "time": "2026-04-20T14:30:05.123Z",
  "settlementDate": "2026-04-22T00:00:00.000Z",
  "accountNumber": "88223344",
  "activityType": "EXECUTION",
  "netAmount": -8762.50,
  "transferItems": [
    {
      "instrument": {
        "symbol": "TSLA",
        "assetType": "EQUITY",
        "description": "TESLA INC",
        "cusip": "88160R101"
      },
      "amount": 50.0,
      "price": 175.25,
      "cost": 8762.50
    }
  ]
}
```

### 4.2. Options & Multi-Leg (Combo) Trades

#### Option Specifics
When `assetType` is `OPTION`, the `instrument` object expands to include the OSI (Option Standard Identifier) components:

```json
"instrument": {
  "symbol": "AAPL  260619C00200000",
  "assetType": "OPTION",
  "type": "VANILLA",
  "putCall": "CALL",
  "underlyingSymbol": "AAPL",
  "optionExpirationDate": "2026-06-19T00:00:00.000Z",
  "optionStrikePrice": 200.00,
  "instruction": "BUY_TO_OPEN"
}
```

#### Combo / Multi-Leg Trades
Complex trades (e.g., Vertical Spreads, Iron Condors) are typically represented by a single `orderId` linked to multiple transaction items. To map these to TradeSensei as a unified trade:
- **Grouping:** Group objects by `orderId`.
- **TransferItems:** Multiple `transferItems` will appear in a single transaction if legs were filled simultaneously.
- **Net Cost:** Calculate net premium by summing the `cost` fields (Negative for credits, Positive for debits).

*Example: Bull Call Spread (2 Legs)*
```json
{
  "orderId": 12345678,
  "type": "TRADE",
  "activityType": "EXECUTION",
  "transferItems": [
    {
      "instrument": { "symbol": "XYZ 260515C00050000", "assetType": "OPTION" },
      "amount": 1,
      "price": 5.20,
      "positionEffect": "OPENING"
    },
    {
      "instrument": { "symbol": "XYZ 260515C00055000", "assetType": "OPTION" },
      "amount": 1,
      "price": 2.10,
      "positionEffect": "OPENING"
    }
  ]
}
```

---

## 5. TradeSensei Mapping Table

| Schwab Source Field | Logic / Note | TradeSensei Field |
| :--- | :--- | :--- |
| `activityId` | Unique ID for the activity | `external_id` |
| `orderId` | Identifies legs of a combo; used for grouping | `group_id` / `order_ref` |
| `time` / `tradeDate` | ISO-8601 execution time | `execution_time` |
| `transferItems[].amount` | Quantity filled | `quantity` |
| `transferItems[].price` | Per unit price | `price` |
| `transferItems[].instrument.assetType` | E.g., `EQUITY`, `OPTION` | `asset_class` |
| `transferItems[].instrument.symbol` | Ticker or Option OSI | `symbol` |
| `transferItems[].cost` (or `netAmount`) | Used to calculate net credit/debit | `net_cost` |
| `transferItems[].feeType` | Aggregate regulatory / commission fees | `commission` |

---

## 6. Error Handling & Rate Limits

- **429 Too Many Requests**: Schwab imposes a burst limit of 10 requests per second and a daily quota per API Key.
- **500/503 Internal Server Error**: Common during Schwab's maintenance windows (typically 12:00 AM – 3:00 AM ET).
- **Retry Logic**: Implement exponential backoff for 429 and 503 errors.

---

## 7. Official Documentation References

- **Schwab Developer Portal**: [https://developer.schwab.com/products/individual-trader-api](https://developer.schwab.com/products/individual-trader-api)
- **API Specification (Swagger/OAS)**: `v1.2.0-trader` - Transactions Section.
- **Authentication Guide**: OAuth 2.0 Workflow for Retail Accounts (Version 2026.1).
- **Option Standard Identifier (OSI)**: Technical Committee for Clearing Procedures.
