# execution-splitting Specification

## Purpose
When a single broker execution contributes to multiple aggregated trades, the system splits the execution into separate `LogicalExecution` records so each trade receives its own execution leg with the correct quantity allocation, while preserving broker lineage and cross-trade metadata cohesion for a single evolving position.

## Requirements

### Requirement: Split Detection
When a `LogicalExecution` participates in the creation of multiple `TradeCreate` objects during FIFO aggregation, the system SHALL split the execution into separate child records, each with quantity and commission proportionally allocated.

#### Scenario: Execution used by multiple trades is split
- **WHEN** a `LogicalExecution` participates in the creation of multiple `TradeCreate` objects during FIFO aggregation
- **THEN** the system SHALL split the execution into separate child records
- **THEN** each child SHALL have the quantity and commission proportionally allocated

### Requirement: Split Execution Creation
When an execution needs splitting for trade assignment, the system SHALL: soft-delete the original execution (`deleted=true`); create a child execution for the specific trade with `origin='split'`; create a remainder child for future allocation (if quantity remains); set `parent_id` on both children to the original execution ID; and assign `trade_id` to the child belonging to the trade.

#### Scenario: Partial close creates two child executions
- **GIVEN** a 100-share buy execution (`E1`) later closed in a 60+40 sequence via two separate sell imports
- **WHEN** FIFO aggregation assigns the execution to Trade A (60 shares) and Trade B (40 shares)
- **THEN** `E1` is soft-deleted (`deleted=true`, `trade_id=NULL`, `origin='imported'`)
- **THEN** child `E1a` is created with `quantity=60`, `trade_id=TradeA`, `parent_id=E1`, `origin='split'`
- **THEN** child `E1b` is created with `quantity=40`, `trade_id=TradeB`, `parent_id=E1`, `origin='split'`
- **THEN** `GET /api/v1/trades/TradeA/executions` returns `[E1a]` and `GET /api/v1/trades/TradeB/executions` returns `[E1b]`

#### Scenario: No split required for a single complete round-trip
- **GIVEN** a 100-share buy execution (`E2`) closed as one complete 100-share round-trip (Trade C)
- **WHEN** FIFO aggregation assigns the execution directly to Trade C
- **THEN** `E2` receives direct assignment (`trade_id=TradeC`, `origin='imported'`, `deleted=false`)
- **THEN** no child executions are created and `E2.parent_id` remains `NULL`

#### Scenario: Three-way split across three trades
- **GIVEN** a 100-share buy execution (`E3`) closed in a 30+30+40 sequence (Trades D, E, F)
- **WHEN** FIFO aggregation assigns the execution across the three trades
- **THEN** three children `E3a` (30, TradeD), `E3b` (30, TradeE), `E3c` (40, TradeF) are created, each with `parent_id=E3` and `origin='split'`
- **THEN** each trade's executions endpoint returns exactly one execution leg and the child quantities sum to the original quantity (30+30+40=100)

### Requirement: Quantity Conservation
Given an original execution with quantity Q split into N child executions with quantities Q1..QN, the sum Q1 + Q2 + ... + QN SHALL equal Q, and the sum of child commissions SHALL equal the original commission.

#### Scenario: Split quantities and commissions sum to the original
- **GIVEN** an original execution with quantity Q and commission C split into N children
- **WHEN** the split operation completes
- **THEN** the sum of all child quantities SHALL equal Q
- **THEN** the sum of all child commissions SHALL equal C

### Requirement: Broker Integrity Preservation
Given an original execution linked to a `BrokerRawTransaction`, when the execution is split, the lineage to the original BRT SHALL remain traceable via `parent_id`, and no child execution SHALL directly reference the BRT.

#### Scenario: Split children trace lineage via parent_id, not directly to the BRT
- **GIVEN** an original execution linked to a `BrokerRawTransaction`
- **WHEN** the execution is split into child executions
- **THEN** each child's lineage to the original BRT SHALL remain traceable via `parent_id`
- **THEN** no child execution SHALL directly reference the `BrokerRawTransaction`

### Requirement: Metadata Inheritance Across Split-Derived Trades
Given a trade with user-defined metadata (`playbook_id`, `tags`, `notes`, `user_rating`), when execution splitting creates additional trade records belonging to the same business position, the system SHALL apply metadata inheritance so all split-derived trades in that position have equivalent metadata state.

#### Scenario: Split-derived trades inherit the position's metadata snapshot
- **GIVEN** Trade G (`position_id=P1`) has `playbook_id=PB-01`, `tags=["breakout","a-plus"]`, `notes="Initial thesis"`, `user_rating=4`
- **WHEN** a technical split creates Trade G1 and Trade G2 within position P1
- **THEN** Trade G1 and Trade G2 metadata SHALL equal the Trade G metadata snapshot at split time

### Requirement: Position Group Cohesion
When multiple trades represent one evolving position due to partial closes, staggered entries, or split-aware allocation, the system SHALL assign a stable `position_id` (or equivalent group identifier) shared across those trades, and queries for position analysis SHALL be able to aggregate by this identifier.

#### Scenario: Sibling trades from one evolving position share a position_id
- **WHEN** multiple trades represent one evolving position due to partial closes or staggered entries
- **THEN** the system SHALL assign a stable `position_id` shared across those trades
- **THEN** `GET /api/v1/trades?position_id=<id>` SHALL return all sibling trades in that position

### Requirement: Open-Position Metadata Propagation
Given an open position with existing trades sharing one `position_id`, when a user updates propagatable metadata on any trade in that group, the update SHALL be propagated to all eligible sibling trades in the same open position group, and propagation SHALL NOT affect trades from other positions even if symbol/account matches.

#### Scenario: Metadata update propagates to open-position siblings only
- **GIVEN** Trade H1 (day 1, `position_id=P2`, no notes) and Trade H2 (day 10 partial close, `position_id=P2`)
- **WHEN** the user updates Trade H2 with `notes="Scale-out confirmed"` and `tags=["swing","risk-managed"]`
- **THEN** Trade H1's notes/tags SHALL be updated to match the propagated position metadata
- **THEN** Trade H2 SHALL retain the edited values
- **THEN** no trade with `position_id != P2` SHALL be modified, even if it shares the same symbol

#### Scenario: Non-metadata field update does not trigger propagation
- **GIVEN** an open position with sibling trades
- **WHEN** a user updates a non-metadata field (e.g. `symbol`) on one trade
- **THEN** the update SHALL NOT propagate to sibling trades

### Requirement: Quantity Overflow Is Rejected
When allocation requests exceed the original execution quantity, the system SHALL raise a `ValueError` with quantity details, and no split operation SHALL be performed.

#### Scenario: Overflowing quantity allocation is rejected before any write
- **WHEN** a split allocation requests a total quantity exceeding the original execution quantity
- **THEN** the system SHALL raise `ValueError` with quantity details
- **THEN** no split operation SHALL be performed and no DB write SHALL occur

### Requirement: Commission Overflow Is Rejected
When commission allocation exceeds the original execution commission, the system SHALL raise a `ValueError` with commission details, and no split operation SHALL be performed.

#### Scenario: Overflowing commission allocation is rejected before any write
- **WHEN** a split allocation requests a total commission exceeding the original execution commission
- **THEN** the system SHALL raise `ValueError` with commission details
- **THEN** no split operation SHALL be performed

### Requirement: Original Execution Not Found Is Rejected
When attempting to split a non-existent execution ID, the system SHALL raise `ExecutionNotFoundError`, and no child executions SHALL be created.

#### Scenario: Splitting a non-existent execution raises an error
- **WHEN** a split operation targets an execution ID that does not exist
- **THEN** the system SHALL raise `ExecutionNotFoundError`
- **THEN** no child executions SHALL be created

### Requirement: Metadata Propagation Conflict Resolution
When concurrent metadata updates target the same `position_id`, the system SHALL resolve with deterministic last-write-wins using `updated_at`, and SHALL emit an audit-safe conflict log entry.

#### Scenario: Concurrent updates to the same position resolve deterministically
- **WHEN** two concurrent metadata updates target trades sharing the same `position_id`
- **THEN** the system SHALL resolve the conflict using deterministic last-write-wins based on `updated_at`
- **THEN** the system SHALL emit an audit-safe conflict log entry

### Requirement: Split Operation Performance
A split operation into N children SHALL complete within 100ms per child execution, with total import time increase under 20% versus the non-split baseline. For M executions requiring splits during import, total database queries SHALL be O(M), not O(M²).

#### Scenario: Split operation completes within the per-child time budget
- **WHEN** an execution requiring a split into N children is processed
- **THEN** the split operation SHALL complete within 100ms per child execution
- **THEN** the total import time increase SHALL be less than 20% versus the non-split baseline

#### Scenario: Bulk splits scale linearly with execution count
- **WHEN** M executions require splits during a single import
- **THEN** the total database query count SHALL be O(M), not O(M²)

### Requirement: Execution Response Includes Split Lineage
Execution read responses (`GET /api/v1/trades/{trade_id}/executions` and equivalent endpoints) SHALL include split lineage information (`origin`, `parent_id`) alongside the standard execution fields.

#### Scenario: Execution response includes origin and parent_id
- **WHEN** a client requests executions for a trade with split-derived legs
- **THEN** each returned execution SHALL include `origin` (e.g. `"split"`) and `parent_id` referencing the original execution
- **THEN** the trade executions endpoint SHALL return all assigned execution legs for that trade

## Reference: Verification Test Scenarios

The following scenarios define the formal QA acceptance criteria for this capability. Each
maps to unit tests in `backend/tests/unit/test_split_verification_scenarios.py`.

### VT1: Classic Partial Close (FIFO Split — buy 100 / sell 60)
**Unit test class**: `TestScenario1PartialClose`

| Step | Action |
|------|--------|
| 1 | Import BUY 100 AAPL |
| 2 | Assign Playbook "High Tight Flag", Tag "Top 1", Note "Initial entry" to the open trade |
| 3 | Import SELL 60 AAPL |

**Expected assertions**: Two trades created (Trade A: 60, closed; Trade B: 40, open) sharing the same `position_id`; original 100-share execution has `deleted=true`; Trade A links to a 60-share child with `origin='split'` and `parent_id` → original; child quantities and commissions conserve.

**Covered by tests**: `test_two_child_trades_are_created_for_60_40_split`, `test_split_quantities_sum_to_original`, `test_split_commissions_sum_to_original`, `test_original_entry_execution_is_soft_deleted`, `test_metadata_inheritance_assigned_to_split_derived_position_group`

### VT2: Async Metadata Update on Open Position (No Split)
**Unit test class**: `TestScenario2AsyncMetadataUpdate`

| Step | Action |
|------|--------|
| 1 | Import BUY 100 TSLA; trade is open |
| 2 | Set Playbook to "Mean Reversion" via PATCH |
| 3 | Import SELL 100 TSLA (full close next day) |

**Expected assertions**: No split occurs (direct `trade_id` assignment); PATCH propagates metadata to open position siblings; updating a non-metadata field does not propagate; final closed trade retains the Playbook.

**Covered by tests**: `test_direct_assignment_used_for_full_close_no_split`, `test_update_trade_propagates_playbook_to_open_position_siblings`, `test_update_trade_does_not_propagate_when_no_metadata_fields_changed`

### VT3: Multi-Stage Split / Cascading (buy 100 → sell 30, sell 30, sell 40)
**Unit test class**: `TestScenario3MultiStageSplit`

| Step | Action |
|------|--------|
| 1 | Import BUY 100 NVDA |
| 2 | Import SELL 30 NVDA |
| 3 | Import SELL 30 NVDA |

**Expected assertions**: Three trades (30 closed, 30 closed, 40 open) share one `position_id`; all three child executions reference the same `parent_id`; quantities sum to 100; executions used by only one trade are not split.

**Covered by tests**: `test_three_way_split_all_children_share_position_id`, `test_three_way_split_quantities_sum_to_100`, `test_three_way_split_all_children_reference_same_parent_id`, `test_single_execution_id_not_split_when_used_by_one_trade`

### VT4: Broker Integrity & Execution Field Audit
**Unit test class**: `TestScenario4BrokerIntegrityAudit`

**Expected assertions on `GET /api/v1/trades/{id}/executions`**: `origin == "split"` on all child executions; `parent_id` is non-null and points to the original broker execution; `trade_id` on each child matches the trade it was allocated to; `quantity` reflects only the allocated portion; overflow in quantity/commission allocation is rejected before any DB write.

**Covered by tests**: `test_split_children_have_origin_split`, `test_split_children_have_non_null_parent_id`, `test_split_child_trade_ids_match_usage_list`, `test_quantity_overflow_validation_blocks_bad_allocations`, `test_commission_overflow_validation_blocks_bad_allocations`, `test_child_execution_qty_matches_allocated_portion_not_original`

### VT5: Idempotency (Re-Import / Fresh Start)
**Unit test class**: `TestScenario5Idempotency`

| Step | Action |
|------|--------|
| 1 | Run Fresh Start import with partial-close file |
| 2 | Run the same Fresh Start import a second time |

**Expected assertions**: Position ID assignment is a no-op when no execution is shared by multiple trades; empty `trades_with_sources` never queries the DB; an already-set `position_id` on one sibling is reused, not overwritten; propagation is strictly scoped to the source trade's `position_id`.

**Covered by tests**: `test_assign_position_ids_no_op_when_no_multi_trade_executions`, `test_assign_position_ids_with_empty_sources_is_noop`, `test_backfill_with_empty_sources_returns_early`, `test_position_id_reused_when_already_set_on_one_sibling`, `test_propagation_scope_limited_to_open_position_siblings`

## Reference: Validation Queries

After split operations during import, the following invariants MUST hold (used in integration test assertions, not exposed as an API):

```sql
-- All split children must reference a valid parent
SELECT COUNT(*) FROM logical_executions
WHERE origin = 'split' AND parent_id IS NULL;
-- Expected: 0

-- Parent quantities must equal the sum of children quantities
SELECT parent_id,
       parent.quantity as parent_qty,
       SUM(child.quantity) as children_qty
FROM logical_executions child
JOIN logical_executions parent ON child.parent_id = parent.id
WHERE child.origin = 'split'
GROUP BY parent_id, parent.quantity
HAVING parent.quantity != SUM(child.quantity);
-- Expected: 0 rows

-- All non-deleted executions should have a trade assignment or a valid reason
SELECT COUNT(*) FROM logical_executions
WHERE deleted = false
  AND trade_id IS NULL
  AND pnl IS NULL  -- Exclude orphaned closing legs
  AND origin != 'manual';  -- Exclude manual entries
-- Expected: 0 for successful imports
```

## Reference: Response Shape Examples

Execution read response after a split (see "Execution Response Includes Split Lineage"):

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

Trade executions endpoint (`GET /api/v1/trades/{trade_id}/executions`):

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
  "meta": { "total": 1, "has_splits": true }
}
```

Trade read contract (position + metadata context) used by split-aware UI flows:

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

## Reference: Acceptance Checklist

- [x] No empty Execution Legs tables: every trade displays its proportional execution legs
- [x] No manual effort: playbooks/tags are automatically inherited from the open position to all partial closes
- [x] Audit trail: the origin of every split execution is traceable via `parent_id` to the broker raw file
- [x] Quantity correctness: partial trades calculate P&L only on their allocated portion, not the original lot size

## Reference: UI Presentation Notes (non-normative)

These are UI presentation preferences, not hard requirements:

- **Origin badge**: the `ExecutionLegsTable` may display a "Split" badge for `origin='split'` legs.
- **Lineage indicator**: a link to view parent/children relationships may be offered.
- **Quantity highlight**: a visual indication may be shown when an execution's quantity is less than the original quantity.
- **Position/metadata transparency**: execution legs and related trade views may expose a shared `position_id` indicator, a metadata-inheritance marker (e.g. "Inherited from position"), and a clear separation between user-entered and auto-propagated fields.
