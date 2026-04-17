# Trade Detail Page — UI Layout Specification

This document defines the exact section ordering, grid structure, and component
placement for the redesigned Trade Detail page with execution-level granularity.

Reference screenshots: `docs/screenshots/ui-review/02-trade-detail.png` (before)

---

## Full Page Layout (Desktop: lg breakpoint, ≥1024px)

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ‹ Back to Trades                                                         │
│                                                                          │
│ ┌──────────────────────────────────────────────────────────────────────┐ │
│ │ HEADER CARD                                          bg-card rounded │ │
│ │                                                                      │ │
│ │ MSFT  [LONG] [EQUITY]              FINAL P&L    [CLOSED]    [⋮]    │ │
│ │ Opened: Feb 14 • Closed: Feb 19    +$108.50                         │ │
│ │ Account: IBKR Test                              Edit Trade          │ │
│ └──────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│ ┌──────────────────────────────────────────────────────────────────────┐ │
│ │ ⚠ CONFLICT BANNER (only when has_conflict === true)                 │ │
│ │ Position Conflict — execution totals don't match...  [Dismiss]      │ │
│ └──────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│ ┌───────────────────────── LEFT COL ──────────┐ ┌──── RIGHT COL ─────┐ │
│ │              lg:col-span-2                   │ │    lg:col-span-1   │ │
│ │                                              │ │                    │ │
│ │ ┌──────────────────────────────────────────┐ │ │ ┌────────────────┐ │ │
│ │ │ 1. MEDIA & CHARTS CARD                   │ │ │ │ A. PERFORMANCE │ │ │
│ │ │    [Chart | Screenshots] tabs             │ │ │ │                │ │ │
│ │ │    Candlestick chart with per-execution   │ │ │ │ Realized R     │ │ │
│ │ │    markers (arrows on each leg)           │ │ │ │ Planned RRR    │ │ │
│ │ │    Interval toolbar: [1h] [4h] [1d]       │ │ │ │ Initial Risk   │ │ │
│ │ │    + Add TradingView chart link           │ │ │ │ Return %       │ │ │
│ │ └──────────────────────────────────────────┘ │ │ │ Gross P&L      │ │ │
│ │                                              │ │ │ Net P&L        │ │ │
│ │ ┌──────────────────────────────────────────┐ │ │ │ Holding Period │ │ │
│ │ │ 2. EXECUTION SUMMARY CARD                │ │ │ │                │ │ │
│ │ │    "Computed from 3 execution legs"       │ │ │ └────────────────┘ │ │
│ │ │                                          │ │ │                    │ │
│ │ │  Avg Entry    Exit (VWAP)   Tot Qty      │ │ │ ┌────────────────┐ │ │
│ │ │  $373.62      $377.96       25           │ │ │ │ B. PLAYBOOK &  │ │ │
│ │ │                                          │ │ │ │    PSYCHOLOGY  │ │ │
│ │ │  Commission   Stop Loss     Take Profit  │ │ │ │                │ │ │
│ │ │  $2.00        —             —            │ │ │ │ Strategy/Setup │ │ │
│ │ └──────────────────────────────────────────┘ │ │ │ Tags           │ │ │
│ │                                              │ │ │                │ │ │
│ │ ┌──────────────────────────────────────────┐ │ │ └────────────────┘ │ │
│ │ │ 3. EXECUTION LEGS TABLE           [NEW]  │ │ │                    │ │
│ │ │    "Execution Legs (3)"   [+ Add Exec]   │ │ │                    │ │
│ │ │                                          │ │ │                    │ │
│ │ │  # │ DATE        │SIDE│ QTY│PRICE │COMM │ │ │                    │ │
│ │ │  ──┼─────────────┼────┼────┼──────┼─────│ │ │                    │ │
│ │ │  1 │ Feb 14 11:29│ BUY│  25│373.62│$1.00│ │ │                    │ │
│ │ │  2 │ Feb 16 10:15│ BUY│  10│375.00│$1.00│ │ │                    │ │
│ │ │  3 │ Feb 19 11:29│SELL│  35│377.96│$1.00│ │ │                    │ │
│ │ │                               [Collapse] │ │ │                    │ │
│ │ └──────────────────────────────────────────┘ │ │                    │ │
│ │                                              │ │                    │ │
│ │ ┌──────────────────────────────────────────┐ │ │                    │ │
│ │ │ 4. JOURNAL & NOTES                       │ │ │                    │ │
│ │ │    General Note (from trade.notes)        │ │ │                    │ │
│ │ │    ────────────────────────                │ │ │                    │ │
│ │ │    NoteList (trade_notes with categories) │ │ │                    │ │
│ │ │    [+ Add Note]                           │ │ │                    │ │
│ │ └──────────────────────────────────────────┘ │ │                    │ │
│ │                                              │ │                    │ │
│ └──────────────────────────────────────────────┘ └────────────────────┘ │
│                                                                          │
│ [AddExecutionModal — hidden until triggered]                             │
│ [MergePreviewModal — hidden until triggered]                             │
│ [TradePickerModal  — hidden until triggered]                             │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Section Ordering (Top to Bottom)

| Order | Section                  | Grid Position      | Component                    | New/Changed |
|-------|--------------------------|--------------------|-----------------------------|-------------|
| 0     | Back link                | Full width         | `<Link>`                     | Unchanged   |
| 1     | Header Card              | Full width         | Header with symbol, badges, P&L, overflow menu (⋮) | **Changed**: added ⋮ menu, removed "Partial Close" button |
| 2     | Conflict Banner          | Full width         | `ConflictBanner`             | **New**: only renders when `has_conflict` |
| 3     | Media & Charts           | Left col (2/3)     | `MediaChartsCard`            | **Changed**: chart markers now per-execution |
| A     | Performance              | Right col (1/3)    | Performance metrics card     | **Changed**: SL/TP now inline-editable (click-to-edit) |
| 4     | Execution Summary        | Left col (2/3)     | `ExecutionSummaryCard`       | **New**: replaces flat "Execution Details" grid |
| B     | Playbook & Psychology    | Right col (1/3)    | Strategy/tags card           | **Changed**: Playbook dropdown + Tags multi-select now inline-editable |
| 5     | Execution Legs Table     | Left col (2/3)     | `ExecutionLegsTable`         | **New**: collapsible table with per-execution rows |
| 6     | Journal & Notes          | Left col (2/3)     | `NoteList` + general note    | Unchanged   |

---

## Header Card Detail

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  ┌─ LEFT ───────────────────────────────┐  ┌─ RIGHT ──────────────┐ │
│  │                                       │  │                      │ │
│  │  MSFT  [LONG] [EQUITY]               │  │ FINAL P&L            │ │
│  │  Opened: Feb 14 • Closed: Feb 19     │  │ +$108.50             │ │
│  │  Account: IBKR Test                   │  │                      │ │
│  │                                       │  │ [Manually Edited]    │ │
│  │                                       │  │ [CLOSED]     [⋮]    │ │
│  │                                       │  │                      │ │
│  │                                       │  │ Edit Trade           │ │
│  └───────────────────────────────────────┘  └──────────────────────┘ │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

Overflow menu (⋮) options:
┌────────────────────┐
│ Merge with...       │
│ Correct Trade...    │
│ ──────────────────  │
│ Delete Trade        │
└────────────────────┘
```

**Changes from current:**
- "Partial Close" button **removed** (replaced by "+ Add Execution" in the legs table)
- "Edit Trade" button **removed** — SL/TP/Playbook/Tags are now inline-editable directly in their cards
- Overflow menu (⋮) **added** — contains Merge, Correct Trade (for rare symbol/asset class fixes), Delete
- There is **no page-replacing edit form** anymore — all editing is inline on the normal view

---

## Execution Summary Card Detail

```
┌──────────────────────────────────────────────────────────────────┐
│ Execution Summary                                 ℹ Computed     │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ Avg Entry ⓘ │  │ Exit VWAP ⓘ│  │ Quantity  ⓘ │             │
│  │ $373.62     │  │ $377.96     │  │ 35          │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ Commission ⓘ│  │ Stop Loss ⓘ│  │ Take Prof ⓘ│             │
│  │ $3.00       │  │ —           │  │ —           │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                  │
│  ℹ Values are computed from 3 execution legs below              │
└──────────────────────────────────────────────────────────────────┘
```

- `bg-card rounded-xl border border-border p-5 shadow-sm`
- "ℹ Computed" badge: `text-xs bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400 px-2 py-0.5 rounded`
- MetricHelpLink (ⓘ) icons on each value label, same as current

---

## Execution Legs Table Detail

```
┌──────────────────────────────────────────────────────────────────┐
│ Execution Legs (3)                           [+ Add Execution]   │
│                                                                  │
│ ┌────┬──────────────┬──────┬─────┬─────────┬───────┬────┬─────┐ │
│ │ #  │ Date         │ Side │ Qty │ Price   │ Comm  │P&L │ ⋮   │ │
│ ├────┼──────────────┼──────┼─────┼─────────┼───────┼────┼─────┤ │
│ │ 1  │ Feb 14 11:29 │[BUY ]│  25 │ $373.62 │ $1.00 │ —  │[⋮] │ │
│ │ 2  │ Feb 16 10:15 │[BUY ]│  10 │ $375.00 │ $1.00 │ —  │[⋮] │ │
│ │ 3  │ Feb 19 11:29 │[SELL]│  35 │ $377.96 │ $1.00 │+108│[⋮] │ │
│ └────┴──────────────┴──────┴─────┴─────────┴───────┴────┴─────┘ │
│                                                                  │
│  Each row also shows: [●imported] status badge (after P&L col)   │
│                                                                  │
│                                              [Collapse ▲]        │
└──────────────────────────────────────────────────────────────────┘

Row overflow menu (⋮):
┌──────────────────────┐
│ Edit                  │
│ Move to...            │
│ Detach as new Trade   │
│ ────────────────────  │
│ Delete                │
└──────────────────────┘
```

- `bg-card rounded-xl border border-border shadow-sm`
- Header: `p-5 pb-0` with title + button
- Table: `px-5 pb-5`
- Side badges: [BUY] = `bg-emerald-100 text-emerald-700`, [SELL] = `bg-red-100 text-red-700`
- Status badges: see spec for colors (imported=blue, manual=purple, merged=orange, split=cyan)
- "+ Add Execution" button: `bg-[#6063dd] text-white text-xs px-3 py-1.5 rounded-md`
- P&L column: `—` for opening legs, PnL value with color for closing legs

---

## Performance Card Detail (Right Sidebar — Inline Editable SL/TP)

```
┌────────────────────────────────────┐
│ Performance                        │
│                                    │
│ Realized R ⓘ              +1.25R  │
│ Planned RRR ⓘ            1 : 2.5  │
│ Initial Risk ⓘ            $125.00 │
│ Return % ⓘ                 +1.16% │
│ Gross P&L ⓘ             +$108.50  │
│ Net P&L (after fees) ⓘ  +$106.50  │
│ Holding Period ⓘ            5d 0h │
│ ─────────────────────────────────  │
│ Stop Loss ⓘ          [$148.00] ✎  │  ← click value → inline input
│ Take Profit ⓘ        [$158.00] ✎  │  ← click value → inline input
└────────────────────────────────────┘

After clicking SL value:
┌────────────────────────────────────┐
│ ...                                │
│ Stop Loss ⓘ   [  148.00  ] [✓][✕] │  ← number input + save/cancel
│ Take Profit ⓘ        [$158.00] ✎  │
└────────────────────────────────────┘
```

- SL/TP are displayed as clickable values with a subtle pencil icon (✎)
- Clicking transforms the value into a number input with Save (✓) and Cancel (✕) buttons
- Saving calls `PATCH /api/v1/trades/{id}` with `{ stop_loss: "148.00" }`
- Dependent metrics (Initial Risk, Planned RRR, Realized R) recalculate immediately on save
- Clearing the input and saving sends `null` to remove the SL/TP

---

## Playbook & Psychology Card Detail (Right Sidebar — Inline Editable)

```
┌────────────────────────────────────┐
│ Playbook & Psychology              │
│                                    │
│ Strategy / Setup                   │
│ [Breakout Long ▾]                  │  ← click → dropdown of playbooks
│                                    │
│ Tags                               │
│ [Momentum] [Earnings] [+ Add]      │  ← click → tag picker
│                                    │
└────────────────────────────────────┘

After clicking playbook:
┌────────────────────────────────────┐
│ Strategy / Setup                   │
│ ┌────────────────────────────────┐ │
│ │ Breakout Long              ✓  │ │  ← dropdown open
│ │ Mean Reversion                │ │
│ │ Momentum Scalp                │ │
│ │ None (clear)                  │ │
│ └────────────────────────────────┘ │
└────────────────────────────────────┘

After clicking tags area:
┌────────────────────────────────────┐
│ Tags                               │
│ [Momentum ✕] [Earnings ✕]         │  ← removable badges
│ ┌────────────────────────────────┐ │
│ │ Search tags...                 │ │  ← tag search/picker
│ │ ☐ Gap Play                    │ │
│ │ ☐ High Volume                 │ │
│ │ ☑ Momentum                    │ │
│ │ ☑ Earnings                    │ │
│ └────────────────────────────────┘ │
└────────────────────────────────────┘
```

- Playbook: click the name → dropdown appears, select → auto-saves via PATCH
- Tags: click the tags area → tag picker appears with search, toggle tags → auto-save
- Both save immediately on selection (no explicit Save button needed — optimistic update)

---

## Chart Markers (Inside Media & Charts Card)

```
    Price
    │
540 ┤
    │
520 ┤
    │        ▼ EXIT                    ← arrowDown, #f0abfc
500 ┤        "-35 @ $377.96"              aboveBar
    │       ╔═╗
480 ┤       ║ ║
    │     ╔═╝ ║
460 ┤     ║   ╚═╗
    │   ╔═╝     ║
440 ┤   ║       ╚═╗
    │ ╔═╝         ║
420 ┤ ║           ╚═══
    │ ║
400 ┤ ║
    │ ╚═══════
380 ┤        ▲ ENTRY #1                ← arrowUp, #00d2ff
    │        "+25 @ $373.62"              belowBar
375 ┤              ▲ ENTRY #2          ← arrowUp, #00d2ff
    │              "+10 @ $375.00"        belowBar
360 ┤
    └──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──
      Feb12 14 16 18 19 20 22 24

Same-candle aggregation (if entries 1+2 were on same day):
375 ┤        ▲ ENTRIES                 ← single arrowUp
    │        "+25+10 @ $373/$375"         aggregated label
```

---

## Interaction Map — What Lives Where

There are **two modes** on the Trade Detail page: the **normal view** (default) and
the **edit form** (entered via "Edit Trade"). All execution management happens in
the normal view — the user does NOT need to enter the edit form.

### Normal View (Default — Trade Detail Page)

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  HEADER CARD                                                         │
│  └─ [⋮] Overflow menu ──→ "Merge with..."   → opens TradePickerModal│
│                            "Correct Trade..."→ opens CorrectTradeModal│
│                            "Delete Trade"    → confirm dialog        │
│                                                                      │
│  CONFLICT BANNER (if has_conflict)                                   │
│  └─ [Dismiss] → hides banner (session only, flag stays)              │
│  └─ [Help]    → navigates to help page                               │
│                                                                      │
│  CHART                                                               │
│  └─ Per-execution markers (read-only, no interaction)                │
│                                                                      │
│  EXECUTION SUMMARY CARD                                              │
│  └─ All values read-only (computed). No interactions.                │
│                                                                      │
│  EXECUTION LEGS TABLE  ←── THIS IS THE MAIN ACTION CENTER           │
│  ├─ [+ Add Execution] ──→ opens AddExecutionModal                    │
│  │                         (BUY/SELL toggle, qty, price, date, comm) │
│  │                                                                   │
│  ├─ Click on row ────────→ inline edit mode (price, qty, commission) │
│  │                         [Save ✓] [Cancel ✕]                      │
│  │                                                                   │
│  └─ Row [⋮] menu ───────→ "Edit"                → inline edit mode  │
│                            "Move to..."          → TradePickerModal  │
│                            "Detach as new Trade" → confirm dialog    │
│                            "Delete"              → confirm dialog    │
│                                                                      │
│  JOURNAL & NOTES                                                     │
│  ├─ [+ Add Note] ──→ inline note editor (existing behavior)         │
│  └─ General Note ──→ read-only display (editable via Edit Form)      │
│                                                                      │
│  PERFORMANCE SIDEBAR                                                 │
│  ├─ Computed metrics (read-only): R, RRR, Risk, Return%, PnL        │
│  └─ SL / TP ────────→ click value → inline number input → auto-save │
│                                                                      │
│  PLAYBOOK & PSYCHOLOGY SIDEBAR                                       │
│  ├─ Playbook ────────→ click name → dropdown → auto-save            │
│  └─ Tags ────────────→ click area → tag picker → auto-save          │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### Summary: What triggers what

**There is no separate edit form anymore.** Everything is inline.

| User Action                        | Where                              | Interaction              |
|------------------------------------|------------------------------------|--------------------------|
| Add an execution leg               | Execution table `[+ Add Execution]` | Opens AddExecutionModal  |
| Edit execution price/qty           | Click execution row                | Inline edit in table     |
| Delete an execution                | Row ⋮ menu → Delete                | Confirm dialog           |
| Move execution to another trade    | Row ⋮ menu → Move to...            | TradePickerModal         |
| Detach execution as new trade      | Row ⋮ menu → Detach                | Confirm dialog           |
| Merge with another trade           | Header ⋮ → Merge with...           | TradePickerModal         |
| Edit stop loss / take profit       | Performance Card → click value     | Inline number input      |
| Change playbook                    | Playbook Card → click playbook     | Inline dropdown          |
| Change tags                        | Playbook Card → click tags area    | Inline multi-select      |
| Edit notes (general)               | Journal section                    | Already inline (NoteList)|
| Edit TradingView link              | Chart card                         | Already inline           |
| Correct symbol / asset class       | Header ⋮ → Correct Trade...        | Small correction modal   |

---

## Mobile Layout (< lg, stacked single column)

On viewports below 1024px, the grid collapses to a single column.
All sections stack vertically in this order:

```
┌──────────────────────────────────┐
│ ‹ Back to Trades                 │
│                                  │
│ HEADER CARD (full width)         │
│ MSFT [LONG] [EQUITY]            │
│ +$108.50  [CLOSED] [⋮]          │
│                                  │
│ ⚠ CONFLICT BANNER (if any)      │
│                                  │
│ 📊 MEDIA & CHARTS (full width)  │
│                                  │
│ 📈 PERFORMANCE (full width)     │
│                                  │
│ 📋 EXECUTION SUMMARY (full w.)  │
│                                  │
│ 🎯 PLAYBOOK & PSYCHOLOGY (f.w.) │
│                                  │
│ 📊 EXECUTION LEGS TABLE (f.w.)  │
│                                  │
│ 📝 JOURNAL & NOTES (full w.)    │
└──────────────────────────────────┘
```

**Key difference**: On mobile, Performance and Playbook cards move
**between** the chart and the execution table, because the right column
doesn't exist — everything stacks. This matches the natural reading order:
"What did I trade?" → "How did it perform?" → "What were the executions?"

---

## Component Tree (JSX Structure)

```tsx
<div className="max-w-7xl mx-auto space-y-6">
  {/* 0. Back link */}
  <Link href="/dashboard/trades">‹ Back to Trades</Link>

  {/* 1. Header Card — always visible, no edit mode toggle */}
  <TradeHeader trade={trade} />

  {/* 2. Conflict Banner (conditional) */}
  {trade.has_conflict && <ConflictBanner />}

  {/* 3-6 + A-B: Grid Layout — always the normal view */}
  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

    {/* LEFT COLUMN */}
    <div className="lg:col-span-2 space-y-6">
      {/* 3. Chart */}
      <MediaChartsCard trade={trade} executions={executions} />

      {/* 4. Execution Summary */}
      <ExecutionSummaryCard trade={trade} executionCount={executions.length} />

      {/* 5. Execution Legs Table */}
      <ExecutionLegsTable
        tradeId={trade.id}
        onAddExecution={() => setAddExecOpen(true)}
      />

      {/* 6. Journal & Notes */}
      <JournalNotesCard trade={trade} />
    </div>

    {/* RIGHT COLUMN */}
    <div className="space-y-6">
      {/* A. Performance — SL/TP inline editable */}
      <PerformanceCard trade={trade} onUpdateTrade={updateTrade} />

      {/* B. Playbook & Psychology — Playbook/Tags inline editable */}
      <PlaybookPsychologyCard trade={trade} onUpdateTrade={updateTrade} />
    </div>
  </div>

  {/* Modals (hidden until triggered) */}
  <AddExecutionModal ... />
  <CorrectTradeModal ... />
  <MergePreviewModal ... />
  <TradePickerModal ... />
</div>
```

**Key change from current**: There is no `{isEditing ? <Form/> : <View/>}` toggle anymore.
The page always shows the normal view. All editing is inline within the cards.

---

## Key Differences from Current Layout

| Area                | Before                                | After                                           |
|---------------------|---------------------------------------|-------------------------------------------------|
| Page mode           | `{isEditing ? <Form/> : <View/>}`     | Always normal view — no page-replacing form     |
| Header actions      | "Partial Close" + "Edit Trade"        | Overflow ⋮ (Merge with..., Correct Trade..., Delete) |
| Below header        | Nothing                               | ConflictBanner (conditional, amber)              |
| Section 4 (was Exec Details) | Flat 2×3 grid: entry, exit, qty, comm, SL, TP | `ExecutionSummaryCard` — computed values, no SL/TP (moved to Performance) |
| Section 5           | Did not exist                         | `ExecutionLegsTable` — per-execution rows with inline edit, context menu |
| Chart markers       | 1× arrowUp ENTRY, 1× arrowDown EXIT  | N× arrows, one per execution, same-candle aggregation |
| Journal & Notes     | Position 3 (after exec details)       | Position 6 (after execution legs table) — pushed down |
| Performance card    | Read-only metrics                     | Metrics + **inline-editable SL/TP** (click-to-edit) |
| Playbook card       | Read-only playbook + tags             | **Inline-editable** playbook dropdown + tag picker |
| Modals              | PartialCloseModal                     | AddExecutionModal + CorrectTradeModal + MergePreviewModal + TradePickerModal |
| Deleted             | `TradeEditForm`, `PartialCloseModal`  | Both removed entirely                           |
