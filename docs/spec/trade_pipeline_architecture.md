# Trade Pipeline Architecture & Data Model

This document outlines the architecture of the trade import pipeline, detailing how raw broker data is processed, stored, and aggregated into final closed/open trades. This formalizes the rules implemented to ensure absolute consistency between database-backed imports and in-memory test pipelines (Ground Truth).

## 1. The Three-Layer Data Model

To ensure we never lose the original broker data while allowing users to manually split, merge, or edit executions, the system uses a strict three-layer architecture:

### Layer 1: Raw Data (`BrokerRawTransaction`)
- **Purpose**: An immutable, append-only log of exactly what the broker provided.
- **Characteristics**: 
  - 1:1 mapping to the rows in the XML/CSV export files.
  - Contains a `raw_data` JSON column storing the entire original payload.
  - Uses a composite deterministic ID (`{user_id}:{broker_type}:{transaction_id}`) to ensure idempotency. Re-importing the same file silently skips existing raw transactions.
  - *Data representation in code*: `BrokerRawTransactionCreate` (DTO) and `BrokerRawTransaction` (ORM).

### Layer 2: Logical Data (`LogicalExecution`)
- **Purpose**: The mutable, application-level view of executions.
- **Characteristics**:
  - Upon import, every `BrokerRawTransaction` automatically generates exactly one `LogicalExecution` (Status: `IMPORTED`).
  - Users can manipulate this layer: merging two partial fills into one, or splitting one execution into two (Status: `MERGED`, `SPLIT`, `MANUAL`).
  - This layer isolates user edits from the raw broker source of truth.
  - **Key Property**: Evaluates the `is_mixed_execution` flag (derived from IBKR's `openCloseIndicator` like `C;O` or `O;C`) to detect position flips.

### Layer 3: Presentation Data (`Trade`)
- **Purpose**: The aggregated, round-trip positions (e.g., Buy 100 AAPL, Sell 100 AAPL) representing the actual trader's journal.
- **Characteristics**:
  - Dynamically generated from the `LogicalExecution` layer via the `aggregate_executions_fifo` function.
  - Sits at the end of the pipeline. If a logical execution is edited, the trades are re-aggregated.
  - Calculates the final Gross PnL, Net PnL (Gross minus commissions), entry/exit prices, and time held.

---

## 2. Cash and Side-Effects (`CashTransaction`)

- **Purpose**: Handles all monetary flows that are not direct executions of assets.
- **Includes**: Dividends, deposits, withdrawals, interest, and non-execution fees (e.g., financial transaction taxes or FX conversion fees).
- **Processing**: These bypass the logical execution layer and are written directly to the database. They contribute to the total account balance and cumulative portfolio performance but do not appear as "Trades".

---

## 3. FIFO Aggregation Rules & Pipeline Parity

The aggregation engine (`app/utils/parsers/aggregator.py`) consumes execution-level data and outputs `Trade` objects. 

### Ground Truth (GT) Parity
To ensure absolute mathematical correctness, integration tests (`test_pnl_regression.py`) run a dual-pipeline check:
1. **DB Pipeline**: Parses files -> saves to `BrokerRawTransaction` -> creates `LogicalExecution` -> aggregates to `Trade` -> sums PnL.
2. **Memory Pipeline (GT)**: Parses files directly to `BrokerRawTransactionCreate` DTOs -> skips the DB -> aggregates to `TradeCreate` -> sums PnL.

The system enforces that **both pipelines produce identical exact PnL (to the precision of < 0.01)**. 

### Recent Rule Implementations & Fixes
To maintain this strict parity, the following complex rules are actively enforced:

1. **Position Flips (Mixed Executions)**
   - When a trader reverses a position in a single execution (e.g., holds LONG 5, sells 7, resulting in SHORT 2), brokers like IBKR flag this as `C;O` (Close;Open).
   - **Rule**: If `is_mixed_execution` is True, the aggregator matches the first 5 against the open lot (closing it) and immediately takes the remaining 2 to open a *new* lot in the opposite direction.
   - **Fix**: Both the DB model (`LogicalExecution`) and the pure-memory DTO (`BrokerRawTransactionCreate`) now dynamically evaluate the `raw_data` payload for `C;O` flags. Without this parity, the memory pipeline would treat the remaining 2 as an "orphaned closing lot", breaking the PnL.

2. **Cross-Year Corporate Actions (Splits)**
   - **Rule**: Splits must be applied chronologically during FIFO aggregation. If a position was opened in 2023, and a 1-for-20 reverse split occurs in 2024, the 2023 open lot must be divided by 20 (and its price multiplied by 20) *before* it is matched against a 2024 closing execution.
   - **Implementation**: Handled via the `_apply_split_event` function inside the aggregator queue loop.

3. **Orphaned Lots**
   - **Rule**: If a closing execution has no matching open lot (e.g., because the opening execution happened before the imported date range), it is placed in an `orphaned_lots` queue. It waits there so that if a historical file is imported later, they can be matched up across imports.