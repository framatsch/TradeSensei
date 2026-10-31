# User guide: review trades

Use the Trades list to choose a review set, then move between trades without returning to the list each time. This guide covers desktop and mobile trade review; see the [help and reference glossary](HELP_GLOSSARY.md) for metric definitions.

## How to review a filtered list

1. Select the portfolio you want to review and open **Trades**.
2. Set your filters or open a saved view. For example, choose **Losers** under **Result** to review losing trades.
3. Choose a sort order. On desktop, click a sortable column heading; on mobile, use the sort dropdown, such as **P&L: lowest** or **Closed: newest**.
4. Open a trade by clicking its symbol in the table or tapping its mobile card. Use **Previous** and **Next** on desktop, or the small **‹** / **›** buttons in the mobile header, to continue through the same list.

### Keyboard shortcuts

On a trade detail page, these shortcuts have the same behavior and limits as the navigation buttons:

| Key | Action |
|-----|--------|
| **←** | Open the previous trade in list order |
| **→** | Open the next trade in list order |

Shortcuts do not navigate while focus is in an input, textarea, select, or editable text area. They also do not navigate with **Alt**, **Ctrl**, **Meta/Command**, or **Shift** held, while a menu, modal, dialog, or screenshot lightbox is open, or when another control has already handled the key. Close the overlay and move focus out of the field before using the shortcuts.

### List order, page boundaries, and position

**Previous** means the trade directly above the current trade in the list; **Next** means the trade directly below it. They follow your filters and sort, not necessarily chronological order. Changing the list filters, sort, rows per page, or portfolio starts a new remembered review list when the results load.

Navigation continues across pages. Previously loaded pages are remembered, so moving back to a previous page needs no additional list request. At the end of the last loaded page, **Next** fetches the next page only when you request it, using the same filters, sort, and page size; it then opens that page's first trade. A spinner appears while loading, and both navigation buttons are temporarily disabled.

For example, with **Rows** set to **25**, **Next** from the 25th trade loads the next page and opens trade 26. **Previous** from trade 26 returns to trade 25 without fetching another list page. **Previous** is disabled at the start of the list, and **Next** is disabled at its end.

The position indicator, such as **25 / 128**, means the 25th trade out of 128 results in that list. A **—** total means the count is unavailable. On desktop, hover over the indicator to see its source: **View: Swing A+** for a saved view named Swing A+, **Filtered trade list**, or **All trades**. Button tooltips show the shortcut and the neighboring symbol when it is already known, for example **Next: TSLA (→)**.

### Which list is remembered

This remembered review list is called the **list context**. It contains the active portfolio, the filters actually applied, sort, page size, active saved view, total count, and ordered trades from loaded pages. It lives in this browser tab's session storage and survives a reload, but it is not synchronized with other tabs or devices, or stored with your account.

Previous/Next controls and the position indicator appear only when the stored context belongs to the active portfolio and contains the current trade ID. Opening a bookmark, shared link, or trade from another screen does not create a context. Such a direct link has no navigation controls unless this tab already has a matching context containing that trade; merely matching the filters is not enough. Open the trade from **Trades** to establish a review list.

The stored order is a snapshot, not a live search on every trade page. If a trade is edited, merged, or deleted after the list loads, return to **Trades** to refresh the results and context.

### Return to the list

Use **Back to Trades**, or the back arrow at the left of the mobile header, to restore the stored filters, sort, page size, and active saved view for the current portfolio. The list opens on **page 1**, not the exact page or cursor you left. Without a matching portfolio context, the link opens the regular Trades page without a restored list query.

The browser's **Back** button is different: Previous/Next replace the current trade in browser history, so Back skips the intermediate trades and returns to the page you came from, usually the list. Use **Previous** or **←** to revisit the preceding trade in your review.

### Keep unsaved journal changes

If the journal or its playbook, tags, or annotations have unsaved changes, **Previous** and **Next** ask **“Discard unsaved changes to this trade?”** before leaving. This applies to both buttons and keyboard shortcuts. When Next needs another page, the check uses your latest edits immediately before leaving, including edits made while that page loads.

Cancel the confirmation to stay on the current trade with the draft intact, or confirm to discard the changes and continue. Save first if you want to keep them. This confirmation covers Previous/Next navigation; do not rely on it for **Back to Trades**, browser Back, or a reload.

## How to review a trade on mobile

Below **1024 px** wide, trade details use a compact header and three tabs. The header shows P&L, Realized R, Return %, dates, and holding time; unavailable values display **—**. The header's **⋯** menu contains **Correct Trade…** and **Merge with…**.

| Tab | What to use it for |
|-----|--------------------|
| **Overview** | The default tab: charts and screenshots, risk and performance metrics, editable Stop Loss and Take Profit, and the execution summary |
| **Journal** | Playbook, tags, annotations, Markdown journal, and Quick Notes when enabled |
| **Executions (n)** | Individual execution cards; the count excludes deleted executions |

Switching tabs keeps the hidden panes loaded, so chart state and unsaved journal drafts remain intact. Switching tabs does not save the draft. A dot on **Journal** marks unsaved changes; return to that tab and use the fixed bottom **Save** / **Cancel** bar to save or discard them.

In **Executions**, use a card's **⋯** menu for **Edit** and other available actions, such as splitting or linking a broker transaction. Edit opens a stacked form with its own **Save** / **Cancel** controls. Use **Show deleted** and **Restore** to recover a deleted execution. A conflict banner's **Review** action opens this tab and scrolls to the executions.

## How to filter trades on mobile

Tap **Filter** above the cards. Its count and the counts on the filter tabs show active filters. The bottom sheet groups the controls as follows:

| Group | Filters |
|-------|---------|
| **Trade** | Included/excluded symbols, direction, status, result, asset class |
| **Time** | Opened and closed date ranges, hour of day, day of week |
| **Journal** | Playbook, taxonomy tags, annotation filters |
| **Account** | Account, execution state, needs linking |

Filters **apply immediately** as you change them; **Show results** only closes the sheet. Closing with **×**, tapping outside, or pressing **Esc** also keeps those changes. **Clear all** in the sheet, or **Clear** beside Filter, resets the filters. If open positions are missing, enable **Show Open Trades** in **Settings → Features**; otherwise the list remains restricted to closed trades and the status control is hidden.

Use **Save View** in the sheet footer to reuse a filter set. An active personal saved view also offers **Update**, **Rename**, and **Delete View**. Change the sort with the list dropdown, and use **Rows**, **‹ Prev**, and **Next ›** below the cards to change page size or page through results.

## How to select trades on mobile

1. Tap **Select** to reveal card checkboxes. Tapping a card now toggles its selection instead of opening the trade.
2. Select individual cards or use **Select all on page**. This selects the current page, not every filtered result.
3. Use the fixed bottom bar for **Playbook**, **Tags**, or **Delete**. **Merge** appears when at least two trades are selected. Check the selection count before confirming an action.
4. Tap **Done** to exit selection mode and clear the selection. The bottom bar disappears, and card taps open trades again.

When Quick Notes are enabled, tapping a card's notes badge opens the note input without navigating to the trade.

## Troubleshooting

- **No Previous/Next controls:** Open the trade from the Trades list in the same tab and portfolio. Missing, invalid, or unavailable browser session storage also prevents restoring navigation context.
- **Next cannot load more trades:** The page shows **Could not load the next trades. Please try again.** Stay on the current trade and retry **Next** after checking your connection.
- **A reviewed trade no longer opens:** It may have been deleted or merged since the list loaded. Use **Back to Trades** to refresh the review set.
