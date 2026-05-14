## Why

The Trade Detail page was built incrementally and now contains structural debt: the taxonomy/annotation system (fully implemented in the backend) is invisible to users, the page layout buries key qualitative metadata under legacy "Playbook & Psychology" and "Trade Images" components, and the execution legs table causes horizontal scrolling when embedded in the two-column grid. A focused UI redesign aligns the page with the completed 2x2 metadata model and improves analytical flow by prioritizing information vertically.

## What Changes

- **Remove** `TradeImageGallery` block from the left column (screenshots already accessible via the Screenshots tab inside `MediaChartsCard`)
- **Move** Stop Loss / Take Profit fields from inline position in the Performance card to the **top** of the Performance card (above the computed metrics)
- **Replace** the "Playbook & Psychology" card with a new full-width "Qualitative Analysis & Metadata" section containing:
  - Trade Taxonomies multi-select (wired to `useTradeMetadata`)
  - Trade Annotations dynamic inputs (typed rendering per definition type: `int`/`float` → number input, `bool` → toggle, `string_enum` → dropdown)
  - Journal / Notes textarea (full-width, replaces the current scattered Notes card)
- **Move** `ExecutionLegsTable` out of the two-column grid into a standalone full-width container at the bottom of the page
- **Remove** `InlineTagsField` and `InlinePlaybookField` inline components from `page.tsx` and all associated state/hook wiring (old flat Tags system)
- **Remove** `TradeImageGallery` component usage (component file can remain for other potential uses but is no longer rendered here)
- Wire `useTradeMetadata`, `useTaxonomies`, and `useAnnotationDefinitions` hooks into the page

## Capabilities

### New Capabilities
- `trade-detail-metadata-panel`: Full-width qualitative metadata panel with Trade Taxonomies multi-select, typed Trade Annotation inputs, and an integrated journal textarea

### Modified Capabilities
- `trade-metadata-assignment`: The assignment UI moves from non-existent to the Trade Detail page; the spec now governs the dynamic input rendering rules per annotation type

## Impact

- **Modified file**: `frontend/app/dashboard/trades/[id]/page.tsx` — layout restructure, hook wiring, legacy removal
- **New component**: `frontend/components/trades/QualitativeMetadataPanel.tsx`
- **New component**: `frontend/components/trades/AnnotationInput.tsx` (dynamic typed renderer)
- **Removed from page**: `TradeImageGallery`, `InlineTagsField`, `InlinePlaybookField` inline components, `useTags` and `usePlaybooks` hook calls from this page
- **No backend changes** — all APIs are live
- **No breaking changes to other pages** — tags/playbooks remain on other pages; only removed from Trade Detail
