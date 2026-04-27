# Execution Splitting Behavior Specification

## Overview

When a single broker execution contributes to multiple aggregated trades, the system MUST split the execution into separate LogicalExecution records so each trade receives its own execution leg with the correct quantity allocation.

## Core Requirements

### R1: Split Detection

- **WHEN** a LogicalExecution participates in the creation of multiple TradeCreate objects during FIFO aggregation
- **THEN** the system MUST split the execution into separate child records
- **AND** each child MUST have the quantity and commission proportionally allocated

### R2: Split Execution Creation

- **GIVEN** an execution that needs splitting for trade assignment
- **WHEN** the split operation is performed  
- **THEN** the system MUST:
  1. Soft-delete the original execution (`deleted=true`)
  2. Create child execution for the specific trade with `origin='split'`
  3. Create remainder child for future allocation (if quantity remains)
  4. Set `parent_id` on both children to original execution ID
  5. Assign `trade_id` to the child belonging to the trade

### R3: Quantity Conservation

- **GIVEN** an original execution with quantity Q
- **WHEN** split into N child executions with quantities Q1, Q2, ..., QN
- **THEN** Q1 + Q2 + ... + QN MUST equal Q
- **AND** the sum of child commissions MUST equal original commission

### R4: Broker Integrity Preservation

- **GIVEN** an original execution linked to a BrokerRawTransaction
- **WHEN** the execution is split
- **THEN** the lineage to the original BRT MUST remain traceable via `parent_id`
- **AND** no child execution MUST directly reference the BRT

### R5: Metadata Inheritance Across Split-Derived Trades

- **GIVEN** a trade with user-defined metadata (`playbook_id`, `tags`, `notes`, `user_rating`)
- **WHEN** execution splitting creates additional trade records that belong to the same business position
- **THEN** the system MUST apply metadata inheritance so all split-derived trades in that position have equivalent metadata state

### R6: Position Group Cohesion

- **WHEN** multiple trades represent one evolving position due to partial closes, staggered entries, or split-aware allocation
- **THEN** the system MUST assign a stable `position_id` (or equivalent `group_id`) shared across those trades
- **AND** queries for position analysis MUST be able to aggregate by this identifier

### R7: Open-Position Metadata Propagation

- **GIVEN** an open position with existing trades sharing one `position_id`
- **WHEN** a user updates propagatable metadata on any trade in that group
- **THEN** the update MUST be propagated to all eligible sibling trades in the same open position group
- **AND** propagation MUST NOT affect trades from other positions, even if symbol/account matches

## Scenarios

### Scenario 1: Partial Close Split

**Context**: 100 share buy order, later closed in 60+40 sequence

```
Initial State:
- BRT: user_id:test:T001 → LogicalExecution(id=E1, qty=100, trade_id=NULL)

After FIFO Aggregation:
- Trade A: 60 shares @ entry/exit prices  
- Trade B: 40 shares @ entry/exit prices

Expected Split Result:
- E1: qty=100, deleted=true, trade_id=NULL, origin='imported'
- E1a: qty=60, deleted=false, trade_id=TradeA, parent_id=E1, origin='split'  
- E1b: qty=40, deleted=false, trade_id=TradeB, parent_id=E1, origin='split'
```

**Verification**:
- `GET /api/v1/trades/TradeA/executions` returns [E1a] 
- `GET /api/v1/trades/TradeB/executions` returns [E1b]
- E1a.quantity + E1b.quantity = E1.quantity
- E1a.parent_id = E1b.parent_id = E1.id

### Scenario 2: No Split Required

**Context**: 100 share buy order, closed as complete 100 share trade

```
Initial State:
- BRT: user_id:test:T002 → LogicalExecution(id=E2, qty=100, trade_id=NULL)

After FIFO Aggregation:  
- Trade C: 100 shares @ entry/exit prices (complete round-trip)

Expected Direct Assignment:
- E2: qty=100, deleted=false, trade_id=TradeC, origin='imported'
```

**Verification**:
- `GET /api/v1/trades/TradeC/executions` returns [E2]
- No child executions created
- E2.parent_id remains NULL

### Scenario 3: Three-Way Split

**Context**: 100 share buy order, closed in 30+30+40 sequence

```
Initial State:
- BRT: user_id:test:T003 → LogicalExecution(id=E3, qty=100, trade_id=NULL)

After FIFO Aggregation:
- Trade D: 30 shares @ entry/exit prices
- Trade E: 30 shares @ entry/exit prices  
- Trade F: 40 shares @ entry/exit prices

Expected Split Result:
- E3: qty=100, deleted=true, trade_id=NULL, origin='imported'
- E3a: qty=30, deleted=false, trade_id=TradeD, parent_id=E3, origin='split'
- E3b: qty=30, deleted=false, trade_id=TradeE, parent_id=E3, origin='split'
- E3c: qty=40, deleted=false, trade_id=TradeF, parent_id=E3, origin='split'
```

**Verification**:
- Each trade's executions endpoint returns exactly one execution leg
- Total child quantities = original quantity (30+30+40=100)
- All children have same parent_id

### Scenario 4: Metadata Inheritance on Split

**Context**: A trade with playbook/tags/notes/rating is split into two child trades.

```
Initial State:
- Trade G (position_id=P1):
  playbook_id=PB-01
  tags=["breakout", "a-plus"]
  notes="Initial thesis"
  user_rating=4

Split Event:
- Technical split creates Trade G1 and Trade G2 in position P1

Expected Result:
- Trade G1 metadata == Trade G metadata snapshot
- Trade G2 metadata == Trade G metadata snapshot
```

**Verification**:
- `GET /api/v1/trades?position_id=P1` returns all sibling trades with consistent metadata values

### Scenario 5: Delayed Open-Position Update Propagation

**Context**: Entry on day 1, partial close on day 10, user adds tags/notes on day 10.

```
Initial State:
- Trade H1 (day 1, position_id=P2) created without notes
- Trade H2 (day 10 partial close, position_id=P2)

User Action:
- Update Trade H2 notes="Scale-out confirmed", tags=["swing", "risk-managed"]

Expected Result:
- Trade H1 notes/tags are updated to match propagated position metadata
- Trade H2 retains the edited values
- No trade with position_id != P2 is modified
```

**Verification**:
- Fetch all trades in P2 and confirm metadata convergence
- Fetch trades with same symbol outside P2 and confirm no mutation

## Error Conditions

### E1: Quantity Overflow

- **WHEN** allocation requests exceed original execution quantity
- **THEN** system MUST raise `ValueError` with quantity details
- **AND** no split operation MUST be performed

### E2: Commission Overflow  

- **WHEN** commission allocation exceeds original execution commission
- **THEN** system MUST raise `ValueError` with commission details
- **AND** no split operation MUST be performed

### E3: Original Execution Not Found

- **WHEN** attempting to split a non-existent execution ID
- **THEN** system MUST raise `ExecutionNotFoundError`
- **AND** no child executions MUST be created

### E4: Metadata Propagation Conflict

- **WHEN** concurrent metadata updates target the same `position_id`
- **THEN** system MUST resolve with deterministic last-write-wins using `updated_at`
- **AND** emit an audit-safe conflict log entry

## Performance Requirements

### P1: Split Operation Time

- **GIVEN** an execution requiring split into N children
- **WHEN** the split operation is performed
- **THEN** it MUST complete within 100ms per child execution
- **AND** total import time increase MUST be < 20% vs. non-split baseline

### P2: Database Query Optimization

- **GIVEN** M executions requiring splits during import
- **WHEN** splits are performed  
- **THEN** total database queries MUST be O(M) not O(M²)
- **AND** bulk operations SHOULD be used where possible

## Validation Rules

### V1: Split Consistency Check

After split operations during import:

```sql
-- All split children must reference valid parent
SELECT COUNT(*) FROM logical_executions 
WHERE origin = 'split' AND parent_id IS NULL;
-- Expected: 0

-- Parent quantities must equal sum of children quantities  
SELECT parent_id, 
       parent.quantity as parent_qty,
       SUM(child.quantity) as children_qty
FROM logical_executions child
JOIN logical_executions parent ON child.parent_id = parent.id  
WHERE child.origin = 'split'
GROUP BY parent_id, parent.quantity
HAVING parent.quantity != SUM(child.quantity);
-- Expected: 0 rows
```

### V2: Trade Assignment Completeness

After import completion:

```sql
-- All non-deleted executions should have trade assignment or valid reason
SELECT COUNT(*) FROM logical_executions
WHERE deleted = false 
  AND trade_id IS NULL 
  AND pnl IS NULL  -- Exclude orphaned closing legs
  AND origin != 'manual';  -- Exclude manual entries
-- Expected: 0 for successful imports
```

## API Contract

### Execution Read Response

After split operations, execution responses MUST include lineage information:

```json
{
  "id": "E1a",
  "quantity": "60.00", 
  "price": "243.19",
  "commission": "0.60",
  "trade_id": "TradeA",
  "origin": "split",
  "parent_id": "E1",
  "deleted": false,
  "user_modified": false
}
```

### Trade Executions Endpoint

`GET /api/v1/trades/{trade_id}/executions` MUST return all assigned execution legs:

```json
{
  "data": [
    {
      "id": "E1a",
      "direction": "LONG", 
      "quantity": "60.00",
      "price": "243.19",
      "executed_at": "2024-01-01T15:26:00Z",
      "origin": "split",
      "parent_id": "E1"
    }
  ],
  "meta": {
    "total": 1,
    "has_splits": true
  }
}
```

### Trade Read Contract (Position + Metadata Context)

Trade responses used by split-aware UI flows MUST include:

```json
{
  "id": "TradeA",
  "position_id": "P1",
  "playbook_id": "PB-01",
  "tags": ["breakout", "a-plus"],
  "notes": "Initial thesis",
  "user_rating": 4
}
```

## Verification Test Scenarios

The following five scenarios define the formal QA acceptance criteria for this feature.
Each scenario maps directly to a set of unit tests in
`backend/tests/unit/test_split_verification_scenarios.py`.

### VT1: Classic Partial Close (FIFO Split — buy 100 / sell 60)

**Unit test class**: `TestScenario1PartialClose`

| Step | Action |
|------|--------|
| 1 | Import BUY 100 AAPL |
| 2 | Assign Playbook "High Tight Flag", Tag "Top 1", Note "Initial entry" to the open trade |
| 3 | Import SELL 60 AAPL |

**Expected assertions**:

- Two trades created: Trade A (60, closed), Trade B (40, open)
- Both trades share the same `position_id`
- Original 100-share execution has `deleted=true`
- Trade A is linked to a 60-share child execution with `origin='split'` and `parent_id` → original
- Child quantities 60 + 40 == 100 (quantity conservation)
- Child commissions sum == original commission (commission conservation)

**Covered by tests**:
- `test_two_child_trades_are_created_for_60_40_split`
- `test_split_quantities_sum_to_original`
- `test_split_commissions_sum_to_original`
- `test_original_entry_execution_is_soft_deleted`
- `test_metadata_inheritance_assigned_to_split_derived_position_group`

---

### VT2: Async Metadata Update on Open Position (No Split)

**Unit test class**: `TestScenario2AsyncMetadataUpdate`

| Step | Action |
|------|--------|
| 1 | Import BUY 100 TSLA; trade is open |
| 2 | Set Playbook to "Mean Reversion" via PATCH |
| 3 | Import SELL 100 TSLA (full close next day) |

**Expected assertions**:

- No split occurs: entry execution receives direct `trade_id` assignment
- PATCH triggers metadata propagation to open position siblings
- Updating a non-metadata field (e.g., symbol) does NOT propagate metadata
- Final closed trade retains the Playbook

**Covered by tests**:
- `test_direct_assignment_used_for_full_close_no_split`
- `test_update_trade_propagates_playbook_to_open_position_siblings`
- `test_update_trade_does_not_propagate_when_no_metadata_fields_changed`

---

### VT3: Multi-Stage Split / Cascading (buy 100 → sell 30, sell 30, sell 40)

**Unit test class**: `TestScenario3MultiStageSplit`

| Step | Action |
|------|--------|
| 1 | Import BUY 100 NVDA |
| 2 | Import SELL 30 NVDA |
| 3 | Import SELL 30 NVDA |

**Expected assertions**:

- Three trades: 30 (closed), 30 (closed), 40 (open)
- All three trades share one `position_id` via a single update call
- All three child executions reference the same original parent_id
- Child quantities 30 + 30 + 40 == 100
- Executions used by only one trade are NOT split (direct assignment)

**Covered by tests**:
- `test_three_way_split_all_children_share_position_id`
- `test_three_way_split_quantities_sum_to_100`
- `test_three_way_split_all_children_reference_same_parent_id`
- `test_single_execution_id_not_split_when_used_by_one_trade`

---

### VT4: Broker Integrity & Execution Field Audit

**Unit test class**: `TestScenario4BrokerIntegrityAudit`

**Expected assertions on `GET /api/v1/trades/{id}/executions`**:

- `origin` == `"split"` on all child executions
- `parent_id` is non-null and points to the original broker execution
- `trade_id` on each child matches the trade it was allocated to
- Execution `quantity` reflects only the allocated portion, not the original broker quantity
- Overflow in quantity or commission allocation is rejected before any DB write

**Covered by tests**:
- `test_split_children_have_origin_split`
- `test_split_children_have_non_null_parent_id`
- `test_split_child_trade_ids_match_usage_list`
- `test_quantity_overflow_validation_blocks_bad_allocations`
- `test_commission_overflow_validation_blocks_bad_allocations`
- `test_child_execution_qty_matches_allocated_portion_not_original`

---

### VT5: Idempotency (Re-Import / Fresh Start)

**Unit test class**: `TestScenario5Idempotency`

| Step | Action |
|------|--------|
| 1 | Run Fresh Start import with partial-close file |
| 2 | Run the same Fresh Start import a second time |

**Expected assertions**:

- Position ID assignment is a no-op when no execution is shared by multiple trades
- Empty `trades_with_sources` never queries the DB
- If one sibling already has a `position_id`, it is reused (not overwritten with a new UUID)
- Propagation is strictly scoped to the source trade's `position_id` — other positions are unaffected

**Covered by tests**:
- `test_assign_position_ids_no_op_when_no_multi_trade_executions`
- `test_assign_position_ids_with_empty_sources_is_noop`
- `test_backfill_with_empty_sources_returns_early`
- `test_position_id_reused_when_already_set_on_one_sibling`
- `test_propagation_scope_limited_to_open_position_siblings`

---

## Acceptance Checklist

- [x] No empty Execution Legs tables: every trade displays its proportional execution legs
- [x] No manual effort: playbooks/tags are automatically inherited from the open position to all partial closes
- [x] Audit trail: the origin of every split execution is traceable via `parent_id` to the broker raw file
- [x] Quantity correctness: partial trades calculate PnL only on their allocated portion, not the original lot size

## UI Requirements

### Execution Badge Display

Split executions SHOULD display appropriate badges in the ExecutionLegsTable:

- **Origin Badge**: "Split" for `origin='split'` 
- **Lineage Indicator**: Link to view parent/children relationships
- **Quantity Highlight**: Visual indication when execution quantity < original quantity

### Position/Metadata Transparency

Execution legs and related trade views SHOULD expose:

- Shared `position_id` indicator (or grouped position badge)
- Metadata inheritance marker (e.g., “Inherited from position”)
- Clear separation between user-entered fields and auto-propagated updates
