# UI Design Proposal: Execution-Driven Trade Management

**Status**: Draft — Pending Review  
**Author**: UI/UX Design Session  
**Date**: 2026-04-10  
**Depends on**: `isolated-raw-layer-architecture` (all tasks complete)

---

## 1. Executive Summary

The `isolated-raw-layer-architecture` introduced a two-layer data model: immutable `BrokerRawTransaction` records and mutable `LogicalExecution` records. A `Trade` is now an aggregation of its `LogicalExecution` entries. This proposal defines how the UI adapts to expose execution-level granularity while keeping the interface concise and self-explaining.

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Trade-level computed fields | **Read-only, derived from executions** | Single source of truth. No dual-state confusion. |
| Execution display | **Summary card + expandable execution table** | Quick glance at aggregated values, drill into legs when needed |
| Add execution interaction | **Modal dialog** | Mobile-friendly, pattern-consistent (replaces PartialCloseModal) |
| Merge trades entry | **Both: bulk select in list + "Merge with..." in detail** | Two natural entry points for the same action |
| Merge confirmation | **Preview card** showing combined result | Visual verification before destructive operation |
| Conflict visibility | **Badge on row + banner on detail + "Needs Review" filter** | First-class workflow for discrepancy resolution |
| Raw data visibility | **Logical only by default** (raw hidden) | Feature-toggle-able comparison view for debugging |
| PartialCloseModal | **Replaced** by "Add Exit Execution" | Conceptually cleaner — closing = adding an exit execution |

---

## 2. Current State (Screenshots)

See `docs/screenshots/ui-review/` for reference:

- `01-trades-list.png` — Trade table with checkboxes, direction badges, PnL column
- `02-trade-detail.png` — Header with symbol/direction/status, TradingView chart, flat "Execution Details" grid (entry_price, exit_price, quantity, commission, SL, TP), Performance card, Playbook & Psychology card
- `03-trade-edit-form.png` — Sectioned form: Instrument, Entry/Exit, Timestamps, Tags & Playbook, Notes

---

## 3. Trade Detail Page — Redesigned Layout

### 3.1 Header (Unchanged)

The header area remains as-is:
```
┌─────────────────────────────────────────────────────────────────┐
│ MSFT  [LONG]  [EQUITY]                     FINAL P&L   CLOSED  │
│ Opened: Feb 14, 2026 • Closed: Feb 19, 2026  +$108.50          │
│                                             [Edit Trade]        │
│                                             [⚠ Conflict] *new  │
└─────────────────────────────────────────────────────────────────┘
```

**Changes:**
- Remove "Partial Close" button (replaced by "Add Execution")
- Add "⚠ Conflict" badge (amber) when `trade.has_conflict === true`
- "Edit Trade" button now opens the **metadata-only** edit form (see §5)

### 3.2 Conflict Banner (New)

When `has_conflict` is true, show an amber banner below the header:

```
┌─────────────────────────────────────────────────────────────────┐
│ ⚠ Position Conflict                                            │
│ The logical execution totals don't match the broker's open      │
│ position data. Review the execution legs below and adjust.      │
│                                              [Dismiss] [Help]   │
└─────────────────────────────────────────────────────────────────┘
```

- Background: `bg-amber-50 dark:bg-amber-950/30`
- Border: `border-amber-200 dark:border-amber-800`
- Icon: ⚠ warning triangle
- "Help" links to the help page explaining conflicts

### 3.3 Execution Summary Card (Replaces Current "Execution Details")

The current flat grid showing entry_price / exit_price / quantity / commission / SL / TP is replaced with a **computed summary** card that calculates values from executions:

```
┌─────────────────────────────────────────────────────────────────┐
│ Execution Summary                                    Computed   │
│                                                                 │
│ Avg Entry Price    Exit Price (VWAP)    Total Quantity          │
│ $373.62            $377.96              25                      │
│                                                                 │
│ Total Commission   Stop Loss            Take Profit             │
│ $2.00              —                    —                       │
│                                                                 │
│ ℹ Values are computed from 2 execution legs below              │
└─────────────────────────────────────────────────────────────────┘
```

- Small "ℹ Computed" badge in the top-right to communicate that these aren't editable here
- Subtitle showing execution count: "Values are computed from N execution legs below"
- Entry/exit prices are VWAP (volume-weighted average) when multiple legs exist

### 3.4 Execution Legs Table (New — Below Summary)

A new collapsible section showing individual execution records:

```
┌─────────────────────────────────────────────────────────────────┐
│ Execution Legs (2)                        [+ Add Execution]     │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ # │ DATE          │ SIDE │ QTY │ PRICE   │ COMM  │ STATUS  │ │
│ │ 1 │ Feb 14, 2026  │ BUY  │  25 │ $373.62 │ $1.00 │ ●import │ │
│ │ 2 │ Feb 19, 2026  │ SELL │  25 │ $377.96 │ $1.00 │ ●import │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  [Collapse ▲]                                                   │
└─────────────────────────────────────────────────────────────────┘
```

**Table Columns:**
| Column | Description |
|--------|-------------|
| `#` | Row number (chronological order) |
| `Date` | `executed_at` formatted as "MMM DD, YYYY HH:MM" |
| `Side` | `BUY` (green badge) or `SELL` (red badge) — derived from direction |
| `Qty` | Execution quantity |
| `Price` | Execution price per unit |
| `Comm` | Commission for this leg |
| `P&L` | Broker-reported P&L for closing legs (—for opening legs) |
| `Status` | Status badge: `imported` (blue dot), `manual` (purple dot), `merged` (orange dot), `split` (cyan dot) |

**Row Interactions:**
- **Click row** → Inline edit mode for that execution (price, qty, commission fields become editable inputs). ESC to cancel, Enter to save.
- **Right-click / ⋮ menu** → Context menu with: "Edit", "Delete", "Split Execution"
- On mobile: Tap → open edit modal for that specific execution

**"+ Add Execution" Button:**
- Primary accent button (top-right of section)
- Opens the **Add Execution Modal** (see §4)
- Replaces the old "Partial Close" button entirely

### 3.5 Status Badge Design

| Status | Color | Dot | Meaning |
|--------|-------|-----|---------|
| `imported` | `bg-blue-100 text-blue-700` | 🔵 | Came directly from broker import |
| `manual` | `bg-violet-100 text-violet-700` | 🟣 | Created by user manually |
| `merged` | `bg-orange-100 text-orange-700` | 🟠 | Result of merging executions |
| `split` | `bg-cyan-100 text-cyan-700` | 🔵 | Result of splitting an execution |

### 3.6 Rest of Page (Unchanged)

- Media & Charts card → unchanged
- Journal & Notes → unchanged
- Performance sidebar → unchanged (values still derived from trade-level data)
- Playbook & Psychology → unchanged

---

## 4. Add Execution Modal

### 4.1 Purpose

Replaces `PartialCloseModal`. Used for:
- Adding an exit execution (selling shares to close/partially close)
- Adding an entry execution (scaling into a position)
- Adding a manual execution (corrections)

### 4.2 Layout

```
┌─────────────────────────────────────────────┐
│ Add Execution                            ✕  │
│                                             │
│ ┌─────────────────────────────────────────┐ │
│ │  [  BUY  ] [  SELL  ]                  │ │  ← Segmented toggle
│ └─────────────────────────────────────────┘ │
│                                             │
│ Quantity *                                  │
│ ┌─────────────────────────────────────────┐ │
│ │ e.g. 25                                 │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ Price *                                     │
│ ┌─────────────────────────────────────────┐ │
│ │ e.g. 375.50                             │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ Executed At * (UTC)                         │
│ ┌─────────────────────────────────────────┐ │
│ │ 2026-02-19 11:29                        │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ Commission                                  │
│ ┌─────────────────────────────────────────┐ │
│ │ 0.00                                    │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ P&L (optional, for closing legs)            │
│ ┌─────────────────────────────────────────┐ │
│ │                                         │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│          [Cancel]  [Add Execution]          │
└─────────────────────────────────────────────┘
```

### 4.3 Behavior

- **Side toggle**: BUY = creates a LogicalExecution with direction matching trade open direction. SELL = creates one opposing.
- **Defaults**: Date defaults to now. Commission defaults to 0.
- **Validation**: Qty > 0, Price > 0, Date required.
- **On submit**: POST `/api/v1/trades/{trade_id}/executions` with `status: "manual"`
- **After success**: Modal closes, execution table refreshes, trade summary recalculates, trade list invalidates.

### 4.4 Mobile Adaptation

- Modal goes full-width: `max-w-md` on desktop, `w-full` on mobile
- Fields stack vertically (they already do)
- BUY/SELL toggle stays as full-width segmented control

---

## 5. Edit Trade Form — Scope Reduction

### 5.1 What Changes

The current `TradeEditForm` edits ALL trade fields including quantity, entry_price, exit_price, PnL, and commission. In the execution-driven model, these are **computed values**. The edit form is reduced to **metadata-only fields**.

### 5.2 New Edit Form Sections

| Section | Fields | Editable? |
|---------|--------|-----------|
| Instrument | Symbol, Direction, Asset Class, Currency | Yes — but changes here affect the trade identity, not executions |
| Risk Levels | Stop Loss, Take Profit | Yes — these are trade-level planning fields, not execution-derived |
| Timestamps | Opened At, Closed At | **Read-only** — computed from min/max `executed_at` of executions |
| Computed Values | Quantity, Entry Price, Exit Price, PnL, Commission | **Read-only** — displayed with "ℹ Computed from executions" hint. Link to execution table. |
| Tags & Playbook | Tag multi-select, Playbook dropdown | Yes |
| Notes | Free-text | Yes |
| TradingView | Link field | Yes |

### 5.3 Read-Only Field Display

Computed fields should be clearly distinguished:
```
┌──────────────────────────────────────┐
│ Entry / Exit  (computed from executions)
│                                      │
│ Quantity         Entry Price         │
│ [25     🔒]      [$373.62  🔒]      │  ← Gray background, lock icon
│                                      │
│ Exit Price       PnL                 │
│ [$377.96 🔒]     [+$108.50 🔒]      │
│                                      │
│ Commission                           │
│ [$2.00   🔒]                         │
│                                      │
│ ℹ Edit individual executions in the  │
│   Execution Legs section above       │
└──────────────────────────────────────┘
```

- Background: `bg-secondary/50` (lighter than editable fields)
- Lock icon: 🔒 or small padlock SVG
- Hint text linking back to execution legs section

---

## 6. Merge Trades

### 6.1 Entry Point A: Trade List (Bulk Select)

When 2+ trades are selected via checkboxes in the `TradeTable`:

1. The `BulkActionToolbar` already shows bulk actions
2. Add a new **"Merge"** button (only enabled when 2+ trades selected with the same symbol)
3. Clicking "Merge" opens the **Merge Preview Modal**

**Merge button validation:**
- Same symbol required (show tooltip: "Can only merge trades with the same symbol")
- Same account required
- Same asset class required

### 6.2 Entry Point B: Trade Detail Page

Add a "⋯" overflow menu (kebab menu) in the trade header:

```
┌────────────────┐
│ Edit Trade      │
│ Merge with...   │  ← Opens trade picker
│ Delete Trade    │
└────────────────┘
```

"Merge with..." opens a **Trade Picker Modal** filtered to the same symbol, then proceeds to the Merge Preview.

### 6.3 Merge Preview Modal

```
┌─────────────────────────────────────────────────────────────────┐
│ Merge Trades                                                 ✕  │
│                                                                 │
│ ┌──────────────┐          ┌──────────────┐                     │
│ │ MSFT LONG    │    →     │ MSFT LONG    │                     │
│ │ 25 shares    │          │ 35 shares    │  ← Merged result    │
│ │ 2 executions │          │ 5 executions │                     │
│ │ PnL: +$108   │          │ PnL: +$220   │                     │
│ └──────────────┘          └──────────────┘                     │
│ ┌──────────────┐     ┌──────────────────────────────────────┐  │
│ │ MSFT LONG    │     │ Combined Executions:                 │  │
│ │ 10 shares    │     │ 1. BUY  25 @ $373.62 (Feb 14)       │  │
│ │ 3 executions │     │ 2. BUY  10 @ $373.39 (Feb 12)       │  │
│ │ PnL: +$112   │     │ 3. SELL 25 @ $377.96 (Feb 19)       │  │
│ └──────────────┘     │ 4. SELL 10 @ $384.54 (Feb 16)       │  │
│                      │ 5. ...                                │  │
│                      └──────────────────────────────────────┘  │
│                                                                 │
│ ⚠ This will combine all execution legs into one trade.          │
│   The original trades will be replaced. This cannot be undone.  │
│                                                                 │
│                        [Cancel]  [Merge Trades]                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.4 Merge Backend Behavior

- POST `/api/v1/trades/merge` with `{ trade_ids: [uuid1, uuid2] }`
- Backend:
  1. Verify all trades have the same symbol/account/asset_class
  2. Re-assign all `LogicalExecution` records from trade_ids to a single surviving trade
  3. Re-run aggregation on the surviving trade
  4. Delete the now-empty trades
  5. Return the merged trade

---

## 7. Conflict Resolution ("Needs Review" Workflow)

### 7.1 Trade List — Conflict Badge

In the `TradeRow` component, when `trade.has_conflict` is true:
- Show a ⚠ icon in the Symbol column: `MSFT ⚠`
- Or add a dedicated "Status" column badge

### 7.2 Saved Filter: "Needs Review"

Add a system-level saved filter (`scope: SYSTEM`):
- Name: "Needs Review"
- Filter: `{ has_conflict: true }` (requires backend filter support)
- Show in the sidebar under "TRADING LOG > Trades" sub-items
- Badge count showing number of conflicted trades

### 7.3 Trade Detail — Resolution Flow

The conflict banner (§3.2) provides guidance:
1. User reviews the execution legs
2. User adds/edits/removes executions to reconcile
3. Once totals match, the backend clears `has_conflict` on the next aggregation run
4. Banner disappears

---

## 8. Raw Data Comparison View (Feature Toggle)

### 8.1 Scope

This is an **advanced/debug feature** behind a feature toggle (`features.show_raw_transactions` in UserSettings).

### 8.2 UI

When enabled, the Execution Legs section gains a "View Raw Data" toggle:

```
┌──────────────────────────────────────────────────────────────┐
│ Execution Legs (2)     [View Raw Data ○]     [+ Add Exec]   │
└──────────────────────────────────────────────────────────────┘
```

When toggled ON, show a side-by-side table:

```
│ LOGICAL EXECUTION          │ RAW BROKER DATA              │
│ BUY 25 @ $373.62          │ BUY 25 @ $373.62 (ibkr)     │
│ Status: imported           │ Exec ID: ibkr:2277515525     │
│ Commission: $1.00          │ Raw commission: $1.00        │
```

This view is primarily useful for:
- Debugging import issues
- Verifying corporate action adjustments
- Auditing the mapping between raw and logical layers

---

## 9. New Backend API Endpoints Required

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/v1/trades/{id}/executions` | List LogicalExecutions for a trade |
| `POST` | `/api/v1/trades/{id}/executions` | Add a manual execution to a trade |
| `PATCH` | `/api/v1/executions/{id}` | Update a LogicalExecution (inline edit) |
| `DELETE` | `/api/v1/executions/{id}` | Remove a LogicalExecution |
| `POST` | `/api/v1/trades/merge` | Merge 2+ trades into one |
| `GET` | `/api/v1/executions/{id}/raw` | Get raw transactions for a logical execution (feature toggle) |

### 9.1 New Pydantic Schemas

```python
class LogicalExecutionRead(BaseModel):
    id: UUID
    trade_id: UUID | None
    symbol: str
    direction: Direction
    quantity: Decimal
    price: Decimal
    commission: Decimal
    executed_at: datetime
    pnl: Decimal | None
    status: ExecutionStatus  # imported | manual | merged | split
    currency: str | None
    created_at: datetime
    updated_at: datetime

class LogicalExecutionCreate(BaseModel):
    direction: Direction  # BUY or SELL
    quantity: Decimal
    price: Decimal
    commission: Decimal = Decimal("0")
    executed_at: datetime
    pnl: Decimal | None = None

class MergeTradesRequest(BaseModel):
    trade_ids: list[UUID]  # min 2, max 10
```

### 9.2 New TypeScript Types

```typescript
interface LogicalExecution {
  id: string;
  trade_id: string | null;
  symbol: string;
  direction: Direction;
  quantity: string;
  price: string;
  commission: string;
  executed_at: string;
  pnl: string | null;
  status: "imported" | "manual" | "merged" | "split";
  currency: string | null;
  created_at: string;
  updated_at: string;
}

interface LogicalExecutionCreate {
  direction: Direction;
  quantity: string;
  price: string;
  commission?: string;
  executed_at: string;
  pnl?: string | null;
}

interface MergeTradesRequest {
  trade_ids: string[];
}
```

---

## 10. New Frontend Components

| Component | File | Purpose |
|-----------|------|---------|
| `ExecutionSummaryCard` | `components/trades/ExecutionSummaryCard.tsx` | Computed summary (VWAP entry, total qty, etc.) |
| `ExecutionLegsTable` | `components/trades/ExecutionLegsTable.tsx` | Sortable table of LogicalExecution records |
| `ExecutionRow` | `components/trades/ExecutionRow.tsx` | Single row with inline edit capability |
| `AddExecutionModal` | `components/trades/AddExecutionModal.tsx` | Modal form for creating manual executions |
| `MergePreviewModal` | `components/trades/MergePreviewModal.tsx` | Preview card showing merge result |
| `TradePickerModal` | `components/trades/TradePickerModal.tsx` | Search/select a trade for merging |
| `ConflictBanner` | `components/trades/ConflictBanner.tsx` | Amber alert banner for has_conflict |
| `ExecutionStatusBadge` | `components/trades/ExecutionStatusBadge.tsx` | Colored badge for execution status |

### 10.1 Components to Modify

| Component | Change |
|-----------|--------|
| `TradeDetailPage` (page.tsx) | Add ExecutionLegsTable, ConflictBanner; remove flat Execution Details grid; replace PartialClose with AddExecution |
| `TradeEditForm` | Make qty/entry/exit/pnl/commission read-only with computed badge; remove those from form submission |
| `BulkActionToolbar` | Add "Merge" button (enabled when 2+ same-symbol trades selected) |
| `TradeRow` | Add conflict badge when `has_conflict` |
| `PartialCloseModal` | **Delete** — replaced by AddExecutionModal |

### 10.2 Components to Delete

| Component | Reason |
|-----------|--------|
| `PartialCloseModal.tsx` | Functionality absorbed by `AddExecutionModal` |

---

## 11. Implementation Priority

### Phase 1: Core Execution Display (Must Have)
1. Backend: Execution API endpoints (GET, POST, PATCH, DELETE)
2. Backend: Pydantic schemas for LogicalExecution
3. Frontend: `ExecutionSummaryCard` + `ExecutionLegsTable`
4. Frontend: `AddExecutionModal` (replaces PartialClose)
5. Frontend: Update `TradeDetailPage` layout
6. Frontend: Update `TradeEditForm` to read-only computed fields

### Phase 2: Conflict & Merge (Should Have)
7. Frontend: `ConflictBanner` + conflict badge on TradeRow
8. Backend: Merge trades endpoint
9. Frontend: `MergePreviewModal` + `TradePickerModal`
10. Frontend: "Merge" button in BulkActionToolbar
11. Backend: "Needs Review" system filter

### Phase 3: Polish & Advanced (Nice to Have)
12. Inline editing of execution rows
13. Raw data comparison view (feature toggle)
14. Execution context menu (split, delete)
15. Mobile-optimized execution table (card layout on narrow viewports)

---

## 12. Migration Path

1. **No breaking changes**: The Trade API continues to return the same `TradeRead` schema. Execution data is additive.
2. **Feature flag**: New execution UI can be rolled out behind `features.execution_legs` in UserSettings.
3. **PartialClose deprecation**: Keep the old modal functioning until Phase 1 is complete, then remove.
4. **Backward compat**: Manual trades (created without import) auto-get a single `LogicalExecution` with `status: manual`.

---

## 13. Open Questions

1. **Execution P&L calculation**: Should the frontend compute P&L from executions, or should the backend always return it pre-computed on the Trade?
   - **Recommendation**: Backend computes via aggregator. Frontend displays only.

2. **Re-aggregation trigger**: When a user adds/edits/removes an execution, does the backend automatically re-aggregate the parent trade?
   - **Recommendation**: Yes — every execution mutation triggers re-aggregation of the parent trade.

3. **Execution ordering**: Should executions be sorted by `executed_at` or by creation order?
   - **Recommendation**: `executed_at` ascending (chronological).
