# Trade-Execution Split-Aware Linking

## Problem Statement

After a broker import via the raw pipeline path, all `logical_executions` are created with `trade_id = NULL`, even though trades are correctly aggregated and display P&L values. This causes the `/api/v1/trades/{id}/executions` endpoint to return empty results, preventing the Execution Legs table in the frontend UI from displaying any data.

**Root Cause**: The raw pipeline path in `import_service.py` creates trades through FIFO aggregation (`aggregate_executions_fifo`) but does not write the `trade_id` back into the associated `logical_executions`. The aggregation knows the execution IDs but does not use them for backfilling.

## Proposed Solution: Split-Aware Linking Strategy

**Recommended Strategy**: Split-aware linking — the system detects when an execution is split across multiple trades and automatically splits the database record into correspondingly adjusted child records.

### Example Scenario

```
Original BRT/LogicalExecution:
- user_id:test:T0001 → 100 AAPL @ $243.19 BUY

FIFO Aggregation creates two trades:
- Trade 1: 60 AAPL @ $243.19 (Entry) → $250.00 (Exit) 
- Trade 2: 40 AAPL @ $243.19 (Entry) → open

Split-aware linking creates:
- LogicalExecution 1: 60 AAPL @ $243.19, trade_id=Trade1, parent_id=original, origin='split'
- LogicalExecution 2: 40 AAPL @ $243.19, trade_id=Trade2, parent_id=original, origin='split'
- Original: 100 AAPL @ $243.19, deleted=true

Broker Integrity: parent_id points to the original BRT-linked LogicalExecution
```

## Goals

1. **Complete Post-Trade Analysis**: Each trade receives its exact matching entry/exit legs for grading capabilities
2. **Broker Integrity**: The original 1:1 connection between BRT and LogicalExecution remains traceable via `parent_id`
3. **No Breaking Changes**: Existing FIFO aggregation and simplified-execution-model remain unchanged
4. **Idempotency**: Re-import produces identical results
5. **Metadata Continuity**: Trade-level strategy metadata survives technical splits without user re-entry
6. **Position Cohesion**: Split-derived trades remain part of one business position via stable grouping

## Scope Extension: Metadata Inheritance + Position Management

User feedback identified a functional gap: split-aware execution linking solves technical traceability, but can still break analytical continuity if split-derived child trades lose metadata.

### New Requirements

1. **Automatic metadata inheritance on split**
   - `playbook_id`
   - `tags`
   - `notes`
   - `user_rating`
2. **Stable business-position identifier**
   - Introduce/propagate `position_id` (or equivalent `group_id`) across all trades created from one evolving position.
3. **Open-position propagation**
   - Metadata added after initial entry (e.g., day-10 partial close) must propagate to all related split-derived trades in the same position group.
4. **UI transparency**
   - Execution Legs UI must expose split/position context so users can distinguish technical split from strategy intent.

## Technical Design

### Detection Logic

**Splitting Detection**: An execution must be split when it contributes to multiple `TradeCreate` objects for the same instrument.

```python
# Enhanced in aggregate_executions_fifo:
ExecutionAllocation = {
    'execution_id': UUID,
    'quantity_used': Decimal,
    'trade_create_index': int  # Index in output array
}

# Each TradeCreate tracks its source executions:
TradeCreate = {
    ...,
    'source_executions': List[ExecutionAllocation]
}
```

### Implementation Plan

#### 1. Aggregation Enhancement

**File**: `backend/app/utils/parsers/aggregator.py`

Extend `logical_executions_to_trade_creates()` and `aggregate_executions_fifo()`:

```python
@dataclass
class ExecutionAllocation:
    execution_id: uuid.UUID
    quantity_used: Decimal
    commission_used: Decimal
    
@dataclass  
class TradeCreateWithSources:
    trade_create: TradeCreate
    source_executions: List[ExecutionAllocation]

def aggregate_executions_fifo_with_sources(
    executions: list[TradeCreate],
    ...
) -> List[TradeCreateWithSources]:
    # Enhanced aggregation that tracks ExecutionAllocation
```

#### 2. Import Service Enhancement

**File**: `backend/app/services/import_service.py`

After trade creation (line ~362 `await self._trade_repo.create(trade_with_owner)`):

```python
# New method in ImportService
async def _backfill_execution_trade_links(
    self, 
    trades_with_sources: List[TradeCreateWithSources],
    user_id: uuid.UUID
) -> None:
    """Backfill trade_id in logical_executions using split-aware linking."""
    
    for trade_source in trades_with_sources:
        trade = trade_source.created_trade
        sources = trade_source.source_executions
        
        for allocation in sources:
            # Check if execution needs splitting
            if allocation.quantity_used < execution.quantity:
                await self._split_execution_for_trade(
                    execution_id=allocation.execution_id,
                    quantity_for_trade=allocation.quantity_used,
                    commission_for_trade=allocation.commission_used,
                    trade_id=trade.id,
                    user_id=user_id
                )
            else:
                # Direct assignment - execution fully belongs to this trade
                await self._exec_repo.update_trade_id(
                    allocation.execution_id, 
                    trade.id
                )

async def _split_execution_for_trade(
    self, 
    execution_id: uuid.UUID,
    quantity_for_trade: Decimal,
    commission_for_trade: Decimal,
    trade_id: uuid.UUID,
    user_id: uuid.UUID
) -> LogicalExecution:
    """Split an execution using simplified-execution-model split logic."""
    
    # 1. Load original execution
    original = await self._exec_repo.get_by_id(execution_id)
    
    # 2. Soft-delete original (deleted=true)
    await self._exec_repo.soft_delete(execution_id)
    
    # 3. Create child for this trade
    child_for_trade = await self._exec_repo.create(
        user_id=original.user_id,
        account_id=original.account_id,
        symbol=original.symbol,
        conid=original.conid,
        asset_class=original.asset_class,
        direction=original.direction,
        quantity=quantity_for_trade,
        price=original.price,
        commission=commission_for_trade,
        executed_at=original.executed_at,
        pnl=original.pnl,  # Note: pnl stays with first split 
        currency=original.currency,
        multiplier=original.multiplier,
        origin=EXECUTION_ORIGIN_SPLIT,
        parent_id=original.id,
        trade_id=trade_id
    )
    
    # 4. Create remainder child (for other trades or future allocation)
    remainder_qty = original.quantity - quantity_for_trade
    remainder_commission = original.commission - commission_for_trade
    
    remainder_child = await self._exec_repo.create(
        user_id=original.user_id,
        account_id=original.account_id,
        symbol=original.symbol,
        conid=original.conid, 
        asset_class=original.asset_class,
        direction=original.direction,
        quantity=remainder_qty,
        price=original.price,
        commission=remainder_commission,
        executed_at=original.executed_at,
        pnl=None,  # Remainder gets no pnl
        currency=original.currency,
        multiplier=original.multiplier,
        origin=EXECUTION_ORIGIN_SPLIT,
        parent_id=original.id,
        trade_id=None  # Will be assigned by subsequent trades
    )
    
    return child_for_trade
```

#### 3. Execution Repository Enhancement

**File**: `backend/app/repositories/execution.py`

```python
async def update_trade_id(
    self, 
    execution_id: uuid.UUID, 
    trade_id: uuid.UUID
) -> bool:
    """Update trade_id for a single execution."""
    stmt = (
        update(LogicalExecution)
        .where(LogicalExecution.id == execution_id)
        .values(trade_id=trade_id)
    )
    result = await self.session.execute(stmt)
    await self.session.flush()
    return bool(getattr(result, "rowcount", 0) > 0)
```

### Data Integrity Safeguards

1. **Broker-Original Link**: `parent_id` FK points to the originally BRT-created LogicalExecution
2. **Audit Trail**: `origin='split'` + `parent_id` enable complete traceability  
3. **Import Idempotency**: Re-import deletes existing trades/executions for account (fresh-start)
4. **Quantity Validation**: Sum of split children = original quantity

## Test Cases

### Test Data Enhancement

**File**: `tests/test_data/ibkr/TraderJournal_anonymized_combined.xml`

Add specific split-scenario test cases:

```xml
<!-- Partial Close Scenario: 100 shares buy, close 60, close 40 -->
<Trade accountId="U12345678" symbol="SPLIT_TEST" conid="999001" 
       tradeID="SPLIT_001" quantity="100" tradePrice="100.00" 
       openCloseIndicator="O" buySell="BUY" 
       dateTime="20240701;100000" />
       
<Trade accountId="U12345678" symbol="SPLIT_TEST" conid="999001"
       tradeID="SPLIT_002" quantity="-60" tradePrice="110.00"
       openCloseIndicator="C" buySell="SELL" 
       dateTime="20240702;100000" fifoPnlRealized="600.00" />
       
<Trade accountId="U12345678" symbol="SPLIT_TEST" conid="999001"
       tradeID="SPLIT_003" quantity="-40" tradePrice="105.00" 
       openCloseIndicator="C" buySell="SELL"
       dateTime="20240703;100000" fifoPnlRealized="200.00" />

<!-- Combo Trade Example: Multi-leg option spread -->
<Trade accountId="U12345678" symbol="COMBO_TEST" conid="999002"
       tradeID="COMBO_001" quantity="1" tradePrice="5.50"
       assetCategory="OPT" openCloseIndicator="O" buySell="BUY"
       dateTime="20240704;100000" />
       
<!-- Stock Split Example: 2:1 split -->
<CorporateAction accountId="U12345678" symbol="SPLIT_STOCK" 
                 actionDate="20240705" ratio="2.000000" 
                 oldConid="999003" newConid="999003" />
```

### Unit Test Cases

**File**: `tests/test_services/test_import_service.py`

```python
async def test_split_aware_linking_partial_close():
    """Test that opening 100 shares and closing in 60+40 splits creates proper execution links."""
    # Import scenario: BUY 100, SELL 60, SELL 40
    # Expected: 1 original execution (deleted=true), 2 trades, 3 child executions
    
async def test_split_aware_linking_preserves_broker_integrity():
    """Test that parent_id links maintain traceability to BRT."""
    
async def test_split_aware_linking_idempotent_reimport():
    """Test that re-importing the same file produces identical results."""
    
async def test_combo_trade_execution_linking():
    """Test that COMBO trades properly link their execution legs."""
```

### Integration Test Cases

**File**: `tests/test_integration/test_execution_linking.py`

```python
async def test_execution_legs_api_after_import():
    """Test that GET /api/v1/trades/{id}/executions returns linked executions after import."""
    
async def test_frontend_execution_table_display():
    """Test that ExecutionLegsTable shows proper entry/exit legs."""
```

## Migration Strategy

**No Data Migration Required**: Fresh import will automatically apply split-aware linking.

### Deployment Steps

1. **Code Deploy**: Backend changes to aggregation and import service
2. **Fresh Import Trigger**: Users perform account fresh-start re-import
3. **Verification**: UI Execution Legs tables populate correctly

### Rollback Plan

If issues arise, revert code changes and trigger fresh import with legacy pipeline (fallback to best-effort linking).

## Success Criteria

✅ **Post-Import State**: All `logical_executions` have valid `trade_id` or explicit reason for `NULL`

✅ **API Response**: `GET /api/v1/trades/{id}/executions` returns complete execution legs

✅ **UI Display**: ExecutionLegsTable shows Entry/Exit legs for trade analysis

✅ **Broker Integrity**: Original BRT→LogicalExecution linkage traceable via `parent_id`

✅ **Performance**: Import performance remains within acceptable limits (<5x slowdown)

✅ **Metadata Inheritance**: Split-derived trades retain playbook/tags/notes/rating consistently

✅ **Position Continuity**: Related partial closes/entries remain queryable as one business position via `position_id`/`group_id`

✅ **Open-Position Updates**: Metadata edits on one trade propagate predictably across the active position group

## Implementation Tasks

1. [ ] Enhance aggregation logic to track execution allocations (`aggregator.py`)
2. [ ] Implement split-aware backfilling in import service (`import_service.py`) 
3. [ ] Add execution repository methods for trade_id updates (`execution.py`)
4. [ ] Extend test data with combo trades and stock splits scenarios
5. [ ] Write comprehensive unit and integration tests
6. [ ] Performance testing with large import files
7. [ ] Update API documentation for execution linking behavior
8. [ ] Frontend verification that ExecutionLegsTable displays correctly

## Risk Analysis

**High Risk - Performance**: Splitting executions during import adds computational overhead
- *Mitigation*: Performance testing + optimization, async processing where possible

**Medium Risk - Data Complexity**: Split execution lineage could become complex to debug  
- *Mitigation*: Comprehensive audit trail via `parent_id` + detailed logging

**Low Risk - UI Impact**: ExecutionLegsTable might show unexpected execution counts
- *Mitigation*: Clear badge indicators for split executions (`origin='split'`)
