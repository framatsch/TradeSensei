## 1. Database Models and Migration

- [x] 1.1 Create `BrokerRawTransaction` model with broker execution ID as primary key
- [x] 1.2 Create `LogicalExecution` model with a status flag (`imported`, `manual`, `merged`, `split`)
- [x] 1.3 Create `TransactionExecutionMapping` junction table model
- [x] 1.4 Update `Trade` model to include a `has_conflict` flag and adjust its relationship to point to `LogicalExecution`
- [x] 1.5 Generate and apply Alembic migration to completely drop old execution data and table structures and recreate the new raw and logical schema from scratch
- [x] 1.6 Perform a clean re-import of historical XML files from `./tmp` to initialize the new database structure

## 2. Parser and Importer Updates

- [x] 2.1 Refactor `ibkr_xml.py` to save imported XML executions exclusively as `BrokerRawTransaction` records
- [x] 2.2 Create a translation service that automatically generates `LogicalExecution` entries (with `imported` status) for new raw transactions
- [x] 2.3 Create `TransactionExecutionMapping` links between the newly created raw and logical records

## 3. Aggregation Logic Overhaul

- [x] 3.1 Refactor `aggregator.py` to read executions exclusively from the `LogicalExecution` table
- [x] 3.2 Update dynamic corporate action handling and proportional commission calculation to operate solely on the logical layer
- [x] 3.3 Update the validation logic against the `<OpenPosition>` block to mark a `Trade` as conflicted instead of triggering an automatic `force-closed` closure

## 4. Integration Testing

- [x] 4.1 Develop the `flex_query_aggregation.py` standalone script to compute ground-truth PnL based on the specific logic (commissions, taxes, fees)
- [x] 4.2 Write automated integration tests that populate the database using the historical XML files in `./tmp`
- [x] 4.3 Implement test assertions to verify that the database's aggregated yearly PnL exactly matches the ground-truth script's output
