## Why

The current TradeJournal data model uses a one-dimensional structure where the parser directly converts imported XML elements into intermediate objects and aggregates them chronologically into `Trade` entities. This aggregation is destructive: origin quantities and entry prices are overwritten during splits, and commissions are proportionally divided during FIFO matching. Re-syncing overwrites any manual logical interventions because the FIFO logic matches executions deterministically. Furthermore, validating open positions against the `<OpenPosition>` block forces an incorrect automatic closure (with 0 PnL) if logical modifications do not exactly match the broker's holdings. This change introduces an isolated raw data layer and a logical execution layer to preserve data integrity and allow manual interventions to persist across syncs.

## What Changes

- Introduce a strict two-layer architecture for the data model.
- **New Tables**: `BrokerRawTransaction` (immutable, stores exact broker data, PK is broker execution ID), `LogicalExecution` (application logic/modified executions with status flags: `imported`, `manual`, `merged`, `split`), and `TransactionExecutionMapping` (junction table for n:m relation).
- The existing `Trade` entity will be kept but repurposed to solely act as the aggregation result of the `LogicalExecution` table.
- **Import Process Change**: The parser (`ibkr_xml.py`) will now exclusively save extracted data into `BrokerRawTransaction`. A dedicated service logic will then translate these raw imports into `LogicalExecution` entries.
- **Aggregation Change**: The aggregator (`aggregator.py`) will now exclusively read from the `LogicalExecution` table. Modifications from corporate actions (splits) and proportional commission calculations will happen dynamically on the logical layer without overwriting raw data.
- **Validation Change**: The validation against the `<OpenPosition>` block will compare the logical layer's totals. Instead of forcing a closure (`force-closed`), discrepancies will mark the position as conflicted for manual review.
- **Integration Testing**: Implement a Python script (`flex_query_aggregation.py`) as a ground-truth generator for validation, aggregating trade data annually and factoring in specific transaction tax and fee calculations, and build automated tests against historical XML files.
- **UI Scope**: Limit UI changes strictly to correctly displaying the aggregated executions in the existing tables and trade detail views (manual CRUD for the new logic is out of scope for this iteration).

## Capabilities

### New Capabilities
- `raw-transaction-layer`: Introduces the `BrokerRawTransaction`, `LogicalExecution`, and `TransactionExecutionMapping` models and repositories, establishing the immutable raw data tier and the logical tier.
- `non-destructive-aggregation`: Refactors the aggregator to source exclusively from `LogicalExecution`, performing dynamic corporate action modifications and commission allocations, and changes the open position validation from `force-closed` to `conflicted`.
- `aggregation-integration-testing`: Introduces the `flex_query_aggregation.py` ground-truth generator and automated DB integration tests for historical XML file validations.

### Modified Capabilities
- `trade-import`: The parser now persists raw data to `BrokerRawTransaction` instead of directly mapping to intermediary objects, and delegates the creation of logical executions to a dedicated service.

## Impact

- **Database Schema**: New tables (`BrokerRawTransaction`, `LogicalExecution`, `TransactionExecutionMapping`) and modifications to the role of the `Trade` table.
- **Parser (`ibkr_xml.py`)**: Major refactoring to decouple XML parsing from logical execution creation.
- **Aggregator (`aggregator.py`)**: Complete overhaul to source from `LogicalExecution` and handle validation conflicts.
- **Testing**: New suite of integration tests relying on a new ground-truth generator script and historical XML files.
- **UI**: Minor updates to existing tables and detail views to display data sourced from the new logical layer correctly.
