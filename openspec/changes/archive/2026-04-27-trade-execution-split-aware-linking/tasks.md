# Implementation Tasks: Split-Aware Execution Linking

## Phase 1: Core Infrastructure (Backend)

### 1.1 Aggregation Enhancement
- [x] 1.1.1 Create `ExecutionAllocation` dataclass in `app/utils/parsers/aggregator.py`
- [x] 1.1.2 Create `TradeCreateWithSources` dataclass to track source executions
- [x] 1.1.3 Modify `logical_executions_to_trade_creates()` to add `source_execution_id` field to TradeCreate
- [x] 1.1.4 Enhance `aggregate_executions_fifo()` to track execution allocations during FIFO matching
- [x] 1.1.5 Return `List[TradeCreateWithSources]` instead of `List[TradeCreate]` from aggregation

### 1.2 Execution Repository Enhancement
- [x] 1.2.1 Add `update_trade_id(execution_id, trade_id)` method to `ExecutionRepository`
- [x] 1.2.2 Add `get_by_parent_id(parent_id)` method to query split children
- [x] 1.2.3 Add `find_orphaned_children(user_id, account_id)` method for cleanup
- [x] 1.2.4 Add bulk update method `bulk_update_trade_ids(execution_trade_pairs)` for performance

### 1.3 Import Service Core Logic
- [x] 1.3.1 Add `_backfill_execution_trade_links()` method to `ImportService`
- [x] 1.3.2 Add `_split_execution_for_trade()` method implementing split algorithm
- [x] 1.3.3 Add `_assign_execution_to_trade()` method for direct assignment (no split)
- [x] 1.3.4 Integrate backfilling step after trade creation in raw pipeline
- [x] 1.3.5 Add quantity and commission validation logic

### 1.4 Split Algorithm Implementation
- [x] 1.4.1 Implement split detection logic (execution used by multiple trades)
- [x] 1.4.2 Implement proportional quantity allocation calculation
- [x] 1.4.3 Implement proportional commission allocation calculation
- [x] 1.4.4 Follow simplified-execution-model conventions (soft-delete original, create children)
- [x] 1.4.5 Set correct `origin='split'`, `parent_id`, and `trade_id` on children

## Phase 2: Test Data Enhancement

### 2.1 Test Data Scenarios
- [x] 2.1.1 Add partial close scenario (100 → 60+40) to `TraderJournal_anonymized_combined.xml`
- [x] 2.1.2 Add three-way split scenario (100 → 30+30+40)
- [x] 2.1.3 Add combo trade examples (multi-leg option spreads)
- [x] 2.1.4 Add stock split scenarios with corporate actions
- [x] 2.1.5 Add mixed scenarios combining splits with normal round-trips

### 2.2 Edge Case Test Data  
- [x] 2.2.1 Add zero quantity executions
- [x] 2.2.2 Add fractional share scenarios
- [x] 2.2.3 Add high-frequency partial close sequences
- [x] 2.2.4 Add orphaned closing legs (exits without entries)
- [x] 2.2.5 Add large position sizes for performance testing

## Phase 3: Testing Implementation

### 3.1 Unit Tests - Aggregation
- [x] 3.1.1 Test `ExecutionAllocation` dataclass creation and validation
- [x] 3.1.2 Test `aggregate_executions_fifo()` with source tracking
- [x] 3.1.3 Test proportional quantity allocation calculation
- [x] 3.1.4 Test proportional commission allocation calculation
- [x] 3.1.5 Test edge cases (zero quantities, single allocations)

### 3.2 Unit Tests - Import Service
- [x] 3.2.1 Test split detection logic (when to split vs. direct assign)
- [x] 3.2.2 Test `_split_execution_for_trade()` creates correct children
- [x] 3.2.3 Test quantity conservation (children sum = original)
- [x] 3.2.4 Test commission conservation (children sum = original)
- [x] 3.2.5 Test lineage tracking (`parent_id` relationships)

### 3.3 Unit Tests - Repository
- [x] 3.3.1 Test `update_trade_id()` method updates correct execution
- [x] 3.3.2 Test `get_by_parent_id()` returns all children
- [x] 3.3.3 Test bulk operations for performance
- [x] 3.3.4 Test error handling for invalid execution IDs
- [x] 3.3.5 Test concurrent access safety

### 3.4 Integration Tests
- [x] 3.4.1 Test complete import flow with split scenarios
- [x] 3.4.2 Test API response `GET /api/v1/trades/{id}/executions` after import
- [x] 3.4.3 Test execution legs display in frontend after import
- [x] 3.4.4 Test re-import idempotency (fresh start produces same results)
- [x] 3.4.5 Test large file import performance (>1000 executions)

## Phase 4: Error Handling & Validation

### 4.1 Input Validation
- [x] 4.1.1 Add quantity overflow validation (allocations > original)
- [x] 4.1.2 Add commission overflow validation
- [x] 4.1.3 Add execution existence validation before split
- [x] 4.1.4 Add trade existence validation before assignment
- [x] 4.1.5 Add user ownership validation for cross-user protection

### 4.2 Error Recovery
- [x] 4.2.1 Add transaction rollback on split operation failure
- [x] 4.2.2 Add cleanup for partially created split children
- [x] 4.2.3 Add orphaned execution detection and resolution
- [x] 4.2.4 Add detailed error logging with execution IDs
- [x] 4.2.5 Add retry logic for transient database errors

### 4.3 Validation Queries
- [x] 4.3.1 Add post-import validation for split consistency
- [x] 4.3.2 Add validation for quantity conservation
- [x] 4.3.3 Add validation for commission conservation  
- [x] 4.3.4 Add validation for trade assignment completeness
- [x] 4.3.5 Add validation for lineage integrity

## Phase 5: Performance Optimization

### 5.1 Query Optimization
- [x] 5.1.1 Implement bulk execution updates for better performance
- [x] 5.1.2 Add database indexes for split operation queries
- [x] 5.1.3 Optimize execution allocation tracking during aggregation
- [x] 5.1.4 Add query result caching where appropriate
- [x] 5.1.5 Profile and optimize hot path operations

### 5.2 Memory Optimization
- [x] 5.2.1 Use generators for large execution lists during import
- [x] 5.2.2 Process executions in batches to limit memory usage
- [x] 5.2.3 Minimize object copying during split operations
- [x] 5.2.4 Add memory usage monitoring and alerts
- [x] 5.2.5 Optimize dataclass memory layout for better cache performance

### 5.3 Performance Monitoring
- [x] 5.3.1 Add timing metrics for split operations
- [x] 5.3.2 Add execution count metrics (originals vs. children)
- [x] 5.3.3 Add database query count tracking
- [x] 5.3.4 Add memory usage tracking during import
- [x] 5.3.5 Set up performance regression testing

## Phase 6: Frontend Integration

### 6.1 API Response Enhancement
- [x] 6.1.1 Update `LogicalExecutionRead` schema to include `parent_id`
- [x] 6.1.2 Add lineage information to execution response
- [x] 6.1.3 Add split indicator to trade executions endpoint
- [x] 6.1.4 Update OpenAPI documentation for new fields
- [x] 6.1.5 Add API client regeneration after schema changes

### 6.2 UI Enhancements
- [x] 6.2.1 Add split origin badge to `ExecutionStatusBadge` component
- [x] 6.2.2 Add lineage indicators in `ExecutionLegsTable`
- [x] 6.2.3 Add tooltip showing original execution information
- [x] 6.2.4 Add visual indication for proportionally allocated quantities
- [x] 6.2.5 Test UI rendering with split execution data

## Phase 7: Documentation & Deployment

### 7.1 Documentation Updates
- [x] 7.1.1 Update API documentation with split execution behavior
- [x] 7.1.2 Update user guide with execution linking explanation
- [x] 7.1.3 Create troubleshooting guide for split execution issues
- [x] 7.1.4 Document performance characteristics and limits
- [x] 7.1.5 Create admin guide for debugging split execution problems

### 7.2 Deployment Preparation
- [x] 7.2.1 Create migration plan (no data migration needed)
- [x] 7.2.2 Prepare fresh import instructions for users
- [x] 7.2.3 Set up monitoring and alerting for split operations
- [x] 7.2.4 Create rollback plan and procedures
- [x] 7.2.5 Prepare release notes and user communication

### 7.3 Production Validation
- [x] 7.3.1 Test with production-like data volumes
- [x] 7.3.2 Validate import performance within acceptable limits
- [x] 7.3.3 Test concurrent user imports
- [x] 7.3.4 Validate database resource usage
- [x] 7.3.5 Confirm UI renders correctly with real trade data

## Success Criteria Checklist

- [x] **API Functionality**: `GET /api/v1/trades/{id}/executions` returns complete execution legs
- [x] **UI Display**: ExecutionLegsTable shows entry and exit legs for all trades
- [x] **Data Integrity**: All logical_executions have valid `trade_id` or documented reason for NULL
- [x] **Performance**: Import time increase < 20% compared to baseline
- [x] **Broker Integrity**: Original BRT→LogicalExecution linkage traceable via `parent_id`
- [x] **Idempotency**: Re-import produces identical results
- [x] **Validation**: All quantity and commission conservation rules pass
- [x] **Error Handling**: Graceful handling of edge cases and failures
- [x] **Documentation**: Complete API docs and user guides
- [x] **Testing**: 100% test coverage for split logic with comprehensive scenarios

## Phase 8: Metadata Inheritance + Position Management Extension

### 8.1 Domain Model + Schema
- [x] 8.1.1 Define and document canonical `position_id`/`group_id` naming decision
- [x] 8.1.2 Add/validate trade schema support for position grouping identifier
- [x] 8.1.3 Define propagatable metadata field set (`playbook_id`, `tags`, `notes`, `user_rating`)
- [x] 8.1.4 Add migration(s) and indexes for position-group querying if required

### 8.2 Backend Propagation Logic
- [x] 8.2.1 Implement create-time metadata inheritance for split-derived trades
- [x] 8.2.2 Implement update-time propagation across open position siblings
- [x] 8.2.3 Ensure propagation boundaries respect position_id (no cross-position leakage)
- [x] 8.2.4 Add deterministic conflict resolution for concurrent metadata edits
- [x] 8.2.5 Add audit-safe logging for propagation events (`trade_metadata.propagated`)

### 8.3 API + Frontend Integration
- [x] 8.3.1 Extend API responses with position grouping context where missing
- [x] 8.3.2 Regenerate OpenAPI client if backend contracts change
- [x] 8.3.3 Add UI indicators for inherited metadata in execution/trade views
- [x] 8.3.4 Add UI indicator for shared position grouping in split scenarios

### 8.4 Tests
- [x] 8.4.1 Unit tests for inheritance on split creation (VT1 — `TestScenario1PartialClose`, 5 tests)
- [x] 8.4.2 Unit tests for delayed open-position propagation (VT2 — `TestScenario2AsyncMetadataUpdate`, 3 tests)
- [x] 8.4.3 Unit tests: multi-stage split position_id grouping (VT3 — `TestScenario3MultiStageSplit`, 4 tests)
- [x] 8.4.4 Unit tests: broker integrity audit fields (VT4 — `TestScenario4BrokerIntegrityAudit`, 6 tests)
- [x] 8.4.5 Unit tests: idempotency and propagation boundary (VT5 — `TestScenario5Idempotency`, 5 tests)
- [x] 8.4.6 Integration test: day-1 entry + day-10 partial close propagation flow (requires live DB)
- [x] 8.4.7 Integration test: no propagation across different positions with same symbol (requires live DB)
- [x] 8.4.8 Concurrency test for last-write-wins metadata conflict handling

### 8.5 Documentation + Validation
- [x] 8.5.1 Update user guide with position-based metadata behavior
- [x] 8.5.2 Document propagation rules and known edge cases
- [x] 8.5.3 Add verification test scenarios and acceptance checklist to spec (VT1–VT5 in spec.md)

### Validation evidence coverage (success criteria 105-114)

- [x] 105 API functionality coverage captured (`validation/success-criteria-evidence.md`)
- [x] 106 UI display coverage captured (`validation/success-criteria-evidence.md`)
- [x] 107 Data integrity coverage captured (`validation/success-criteria-evidence.md`)
- [x] 108 Performance coverage captured (`validation/success-criteria-evidence.md`)
- [x] 109 Broker integrity coverage captured (`validation/success-criteria-evidence.md`)
- [x] 110 Idempotency coverage captured (`validation/success-criteria-evidence.md`)
- [x] 111 Quantity/commission validation coverage captured (`validation/success-criteria-evidence.md`)
- [x] 112 Error handling coverage captured (`validation/success-criteria-evidence.md`)
- [x] 113 Documentation coverage captured (`validation/success-criteria-evidence.md`)
- [x] 114 Testing coverage captured (`validation/success-criteria-evidence.md`)
