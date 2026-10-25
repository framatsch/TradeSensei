## Context

Both **Playbooks** (`/dashboard/library/playbooks/[id]`) and **Market Check-ins** (`/dashboard/checkins/[date]`) are qualitative documentation views that combine long-form Markdown notes with structured metadata (tags, target win rate / market indexes, annotations) and visual reference charts (images/screenshots + external links).

Currently:
1. **`PlaybookEditorClient.tsx`** uses `flex flex-col flex-1 min-h-0 h-full` with nested `overflow-y-auto` / `overflow-hidden` panes (`35%` left / `65%` right) inside `DashboardLayout`'s `<main className="flex-1 overflow-y-auto p-4 sm:p-6">`. Because `<main>` is a scrollable block container with padding rather than a constrained flex container, `h-full` inside `PlaybookEditorClient` causes competing scrollbars in preview mode and collapsed/awkward textarea sizing in write mode. Furthermore, placing metadata on the left at 35% width leaves large empty areas in read mode while rendering reference images as tiny `40x40px` file rows.
2. **`CheckinDateClient.tsx` & `CheckinForm.tsx`** center everything in a narrow single-column `max-w-3xl mx-auto` container that stacks Tags, Annotations, Target Market Indexes, Notes (`rows={6}`), Screenshots (`w-32 h-20`), News Links, and bottom Action Buttons vertically. On maximized desktop monitors, this wastes horizontal space and prevents traders from viewing their daily screenshots and annotations side-by-side with their market notes.
3. **Inconsistent Save Behavior & Buffered Metadata Bug**: Saving a Playbook immediately exits edit mode (while leaving `?edit=true` in the URL), whereas saving a Check-in stays in edit mode. Moreover, buffered tags and annotations selected while creating a new Check-in (`isNew`) are stored in component state (`bufferedTagIds`, `bufferedAnnotations`) but never sent to the backend after `createMutation` completes.

## Goals / Non-Goals

**Goals:**
- Unify Playbook detail/editor and Market Check-in detail/editor around a single **Full-Width Document-First Layout with Natural Page Scrolling**:
  - **Desktop (`lg+`)**: Full-width Header Card at the top, **Main Pane (`flex-1`, ~65%) on the left** for Markdown documentation, and **Side Pane (`w-[360px] xl:w-[420px]`) on the right** for Tags/Annotations, 16:9 Chart Thumbnails, and Links.
  - **Mobile (`< lg`)**: Compact Header Card followed by a 2-tab segmented switcher (`[ Document | Details & Media (count) ]`) so mobile users can read/edit Markdown immediately or switch to metadata/media without endless scrolling.
- Standardize the editing workflow across both views with **`Save`** (persists changes, stays in edit mode, also bound to `Cmd/Ctrl + S`), **`Save & Close`** (persists changes, exits edit mode, strips `?edit=true` / `?draft=true`), and **`Cancel`**.
- Provide `< Previous Entry` / `Next Entry >` navigation buttons in the Check-in Header Card that jump directly to the chronologically previous or next **existing** check-in entry (preventing users from landing on empty weekend/holiday forms while browsing their journal).
- Eliminate nested scroll traps in `PlaybookEditorClient` and support auto-growing Markdown textareas with `Write`, `Preview`, and desktop `Split` tabs in both views.
- Persist buffered tags and annotations when creating a new Check-in.

**Non-Goals:**
- Modifying the Market Check-in Overview (`CheckinsPageClient`, `TimelineView`, `GalleryView`) or Playbook List (`PlaybookList`).
- Backend API or database schema changes.
- Adding third-party WYSIWYG editor dependencies.

## UI Mockups

### 1. Desktop (`lg+`) — Playbook Detail / Editor (`/dashboard/library/playbooks/[id]`)

```text
+--------------------------------------------------------------------------------------------------+
| [<- Back]  Breakout Pattern [Edit]                    [Delete]  [Cancel]  [Save]  [Save & Close] |
|            Status: [* Active]   |   Target Win Rate: [ 60.0 % ]                                  |
+--------------------------------------------------------------+-----------------------------------+
| MAIN PANE: STRATEGY DOCUMENTATION (flex-1 / ~65%)            | SIDE PANE (w-[360px] xl:w-[420px])|
| +----------------------------------------------------------+ | +-------------------------------+ |
| | Strategy Rules               [ Write | Preview | Split ] | | | TAGS                          | |
| | -------------------------------------------------------- | | | [Trend Following x] [Mom. x]  | |
| | # Breakout Setup Rules                                   | | | [+ Add tag...              v] | |
| |                                                          | | +-------------------------------+ |
| | ## Entry Criteria                                        | | +-------------------------------+ |
| | 1. Volume must be > 1.5x 20-day average                  | | | IMAGES (2)                    | |
| | 2. Price closes above multi-week resistance              | | | [+ Click, drop or Ctrl+V    ] | |
| |                                                          | | | +-------------+ +-----------+ | |
| | ![Setup](ref:pb_img_01)                                  | | | | 16:9 Chart  | | 16:9 Chart| | |
| |                                                          | | | | setup.png   | | study.png | | |
| | ## Risk Management                                       | | | | [Ref] [Del] | | [Ref][Del]| | |
| | - Hard stop at recent swing low.                         | | | +-------------+ +-----------+ | |
| |                                                          | | +-------------------------------+ |
| | (Full natural document height in Read mode;              | | +-------------------------------+ |
| |  auto-growing min-h-[480px] editor in Edit mode)         | | | EXTERNAL LINKS (1)            | |
| |                                                          | | | -> Technical Study      [Del] | |
| |                                                          | | | Label: [TradingView chart   ] | |
| |                                                          | | | URL:   [https://...     ] [+] | |
| +----------------------------------------------------------+ | +-------------------------------+ |
+--------------------------------------------------------------+-----------------------------------+
```

### 2. Desktop (`lg+`) — Market Check-in Detail / Editor (`/dashboard/checkins/[date]`)

```text
+--------------------------------------------------------------------------------------------------+
| [<- Back]  [< Prev]  October 25, 2026  [Next >]       [Delete]  [Cancel]  [Save]  [Save & Close] |
|            Target Indexes: [ SPY -> ] [ QQQ -> ] [ + IWM ]                                       |
+--------------------------------------------------------------+-----------------------------------+
| MAIN PANE: MARKET NOTES (flex-1 / ~65%)                      | SIDE PANE (w-[360px] xl:w-[420px])|
| +----------------------------------------------------------+ | +-------------------------------+ |
| | Market Notes                 [ Write | Preview | Split ] | | | TAGS & ANNOTATIONS            | |
| | -------------------------------------------------------- | | | Tags:                         | |
| | ## Pre-Market Context                                    | | | [* Bullish] [* FOMC Day]      | |
| | - Overnight futures held 5800 key support level          | | |                               | |
| | - Watching NQ relative strength at the open              | | | Annotations:                  | |
| |                                                          | | | Market Regime  [Trending   v] | |
| | ## Post-Market Review                                    | | | Volatility     [High       v] | |
| | - Clean trend day after 10:00 AM macro release           | | | Mood (1-5)     [ 4 ]          | |
| |                                                          | | +-------------------------------+ |
| | (Full natural document height in Read mode;              | | +-------------------------------+ |
| |  auto-growing min-h-[400px] editor in Edit mode)         | | | SCREENSHOTS (2)               | |
| |                                                          | | | [+ Click, drop or Ctrl+V    ] | |
| |                                                          | | | +-------------+ +-----------+ | |
| |                                                          | | | | 16:9 Chart  | | 16:9 Chart| | |
| |                                                          | | | | SPY_5m.png  | | QQQ_1h.png| | |
| |                                                          | | | +-------------+ +-----------+ | |
| |                                                          | | +-------------------------------+ |
| |                                                          | | +-------------------------------+ |
| |                                                          | | | NEWS LINKS (1)                | |
| |                                                          | | | -> forexfactory.com     [Del] | |
| |                                                          | | | URL:   [https://...     ] [+] | |
| +----------------------------------------------------------+ | +-------------------------------+ |
+--------------------------------------------------------------+-----------------------------------+
```

### 3. Mobile & Small Tablet (`< lg`) — Shared Segmented Pane Switcher

On viewports below `lg` (`< 1024px`), both Playbook and Market Check-in detail views display a 2-tab segmented bar directly under the Header Card:

```text
+----------------------------------------------------+
| [<-]  Breakout Pattern        [Save] [Save & Close]|
|       Status: [* Active]  |  Win Rate: 60.0%       |
+----------------------------------------------------+
|  [ Document ]           [ Details & Media (5) ]    |
+----------------------------------------------------+
|                                                    |
|  When "Document" tab is active (default):          |
|  +----------------------------------------------+  |
|  | Strategy Rules          [ Write | Preview ]  |  |
|  | -------------------------------------------- |  |
|  | # Breakout Setup Rules                       |  |
|  | 1. Volume must be > 1.5x average             |  |
|  | 2. Price closes above resistance             |  |
|  +----------------------------------------------+  |
|                                                    |
|  When "Details & Media" tab is active:             |
|  +----------------------------------------------+  |
|  | 1. TAGS / ANNOTATIONS                        |  |
|  | 2. IMAGES / SCREENSHOTS (16:9 cards)         |  |
|  | 3. EXTERNAL / NEWS LINKS                     |  |
|  +----------------------------------------------+  |
+----------------------------------------------------+
```

## Decisions

### 1. Identical Full-Width Flex/Grid Structure (`Main Pane Left` + `Side Pane Right`)
- **Decision**: Both `PlaybookEditorClient` and `CheckinDateClient`/`CheckinForm` use a full-width vertical container (`w-full space-y-4`) inside `<main>`. Below the `solid-card` Header, a `flex flex-col lg:flex-row gap-6 items-start` places the Markdown Main Pane on the left (`flex-1 min-w-0 w-full`) and the Side Pane on the right (`w-full lg:w-[360px] xl:w-[420px] shrink-0 space-y-4`).
- **Rationale**: Reversing Playbook's old `Left=Metadata / Right=Markdown` to `Left=Markdown / Right=Metadata` matches natural LTR reading priority and makes Playbooks and Check-ins 100% consistent on both maximized monitors and laptops.

### 2. Entry-Based `< Prev` / `Next >` Navigation in Check-in Header
- **Decision**: The `< Previous Entry` and `Next Entry >` buttons in the Check-in Header Card query the list of existing check-in entries (`useCheckinEntries`) sorted by `date`, locate the adjacent existing entry dates (`prevEntryDate` < current `date` < `nextEntryDate`), and navigate directly to `/dashboard/checkins/<prevOrNextDate>`. If no earlier or later entry exists, the respective button is `disabled`.
- **Rationale**: Prevents users from stepping into empty weekend/holiday forms when flipping through their journal entries, while the sidebar Mini-Calendar remains available for selecting arbitrary empty dates.

### 3. CSS-Preserved Mobile Pane Tabs (`Document` | `Details & Media`)
- **Decision**: Maintain a local `mobilePane: "document" | "details"` state (default `"document"`). Both the Main Pane and Side Pane remain mounted in the DOM; on `< lg`, the inactive pane uses `hidden lg:block` (or `hidden lg:flex`) while the active pane uses `block`. The `Details & Media` tab badge displays the sum of assigned tags/annotations + images/screenshots + links.
- **Rationale**: Prevents losing unsaved input state or scroll position when toggling between the Markdown text and attachments/tags on mobile devices.

### 4. Auto-Growing Markdown Textarea + Write / Preview / Split Modes
- **Decision**: In edit mode, the Markdown `<textarea>` uses a comfortable minimum height (`min-h-[480px]` in Playbooks, `min-h-[400px]` in Check-ins) and dynamically adjusts its height (`scrollHeight`) on change so the page scrolls naturally instead of trapping the user inside a small nested scrollbar. On desktop (`lg+`), a `Split` tab renders the `<textarea>` and sanitized GFM preview side by side (`grid-cols-2 gap-4`).
- **Rationale**: Eliminates the scroll bug reported by the user while giving power users live side-by-side Markdown preview on wide screens.

### 5. Unified `Save` + `Save & Close` Action Model & Flushing Buffered Check-in Metadata
- **Decision**: Both Playbook and Market Check-in detail headers expose:
  - **`Save`** (secondary button + `Cmd/Ctrl + S`): Persists all changes (including staged Playbook attachments or buffered Check-in tags/annotations) and **stays in edit mode**.
  - **`Save & Close`** (primary button): Persists all changes, sets `isEditMode(false)`, and strips `?edit=true` / `?draft=true` from the URL.
  - **`Cancel`**: Resets unsaved local form fields back to the last persisted state and sets `isEditMode(false)` (or triggers draft cleanup if an empty new Playbook draft is abandoned).
- When creating a new Check-in (`!entry`), `CheckinDateClient` awaits `createMutation.mutateAsync(payload)` and then immediately dispatches `assignTaxonomyMutation` for each `bufferedTagIds` item and `assignAnnotationMutation` for each non-null `bufferedAnnotations` entry before invalidating queries.

## Risks / Trade-offs

- **[Risk] Existing unit and E2E tests rely on accessible labels and button texts** -> **Mitigation**: Keep `aria-label` attributes (`Back to playbooks`, `Playbook content (Markdown)`, `Toggle active status...`, `Remove tag...`, `Delete...`, `Add link`, etc.) intact, ensure `Save` button still matches `/^save$/i` queries alongside `Save & Close`, and update unit/E2E tests accordingly.
