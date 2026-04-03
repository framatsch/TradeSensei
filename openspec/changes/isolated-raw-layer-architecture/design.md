## Context

Currently, the TradeJournal data model directly processes and aggregates imported XML elements (like IBKR flex queries) into chronological `Trade` entities using a single-layer structure. This approach is destructive: it overwrites original quantities and entry prices during splits, and it splits commissions proportionally based on a rigid FIFO logic. When re-syncing data, any manual logical interventions (e.g., manual splits or merges of executions) are lost because the importer re-evaluates everything from scratch. Furthermore, the system performs a validation against the broker's `<OpenPosition>` block, forcibly closing positions with a 0 PnL if the logical alterations result in discrepancies.

This design introduces a strict two-layer architecture separating the immutable raw data from the mutable logical executions.

## Goals / Non-Goals

**Goals:**
- Implement an immutable `BrokerRawTransaction` table to store exact, unmodified broker data.
- Implement a `LogicalExecution` table with status flags to store the application's view of executions.
- Create a `TransactionExecutionMapping` junction table to support n:m relationships between raw transactions and logical executions.
- Repurpose the existing `Trade` entity to serve solely as the final aggregation result of `LogicalExecution` records.
- Refactor the import process (`ibkr_xml.py`) to persist only to the raw layer, utilizing a dedicated service to generate the initial logical executions.
- Refactor the aggregator (`aggregator.py`) to compute trades exclusively from the logical layer, performing corporate action handling and commission allocation dynamically.
- Change the validation logic so that `<OpenPosition>` discrepancies mark a position as conflicted rather than forcibly closing it.
- Create a ground-truth Python script (`flex_query_aggregation.py`) and an integration test suite validating database PnL against historical XML queries.

**Non-Goals:**
- Implementing UI flows for manual CRUD operations on the new logical layer (e.g., manually creating, splitting, or merging executions). UI changes are limited to correctly rendering the data in existing tables and detail views.

## Decisions

**1. Database Schema Separation**
- *Decision*: Introduce `BrokerRawTransaction`, `LogicalExecution`, and `TransactionExecutionMapping`. The `Trade` entity will be demoted to an aggregate materialized view or purely an output of the `LogicalExecution` aggregation.
- *Rationale*: Isolating the raw broker data ensures that we never lose original execution details (prices, commissions, splits). The logical layer allows users (in future iterations) to manipulate their executions without those changes being destroyed upon the next broker sync. 
- *Alternative*: Adding "manual override" flags directly to `Trade` or existing execution tables, which would complicate the schema and still risk losing raw data.

**2. Logical Execution Status Flags**
- *Decision*: `LogicalExecution` will require a status flag (`imported`, `manual`, `merged`, `split`).
- *Rationale*: This clearly defines the lineage of a logical execution and tells the aggregator and UI whether this execution matches a raw broker transaction 1:1, or if it has been manipulated by the user or a corporate action.

**3. Validation Strategy Update**
- *Decision*: Mismatches between the `<OpenPosition>` block and the logical layer's total quantity will no longer trigger a `force-closed` event with 0 PnL. Instead, the position will be flagged as "conflicted" (e.g., adding a `has_conflict` flag to `Trade`).
- *Rationale*: Forcing a closure corrupts the PnL and trade history. Flagging for manual review correctly delegates the resolution to the user while preserving the actual trade data.

**4. Integration Testing Strategy**
- *Decision*: Build a standalone Python script (`flex_query_aggregation.py`) to act as the source of truth, calculating commissions using `max(abs(ibCommission), abs(commission))` and factoring in `TransactionTax` and `CashTransaction` (FEE category). Automated tests will parse historical XMLs, populate the DB, and compare the DB's yearly PnL with the script's output.
- *Rationale*: Validating complex aggregation logic (especially after migrating the entire persistence layer) requires a reliable external baseline. Testing against historical XML files ensures that real-world edge cases (splits, taxes, fees) are correctly handled by the new dual-layer architecture.

## Risks / Trade-offs

- **Risk: Migration Complexity** -> *Mitigation*: The database migration must carefully copy existing execution data into both `BrokerRawTransaction` and `LogicalExecution` to maintain backward compatibility for existing users without data loss. We must write a robust Alembic data migration.
- **Risk: Aggregation Performance** -> *Mitigation*: The aggregator will now read from `LogicalExecution` instead of building trades from raw XML. We must ensure the database queries fetching logical executions for aggregation are well-indexed (e.g., indexing on instrument, date, and account).
- **Risk: Ground Truth Script Discrepancies** -> *Mitigation*: The `flex_query_aggregation.py` script must be thoroughly unit-tested itself to guarantee it represents an accurate ground truth for IBKR's complex fee structures.
