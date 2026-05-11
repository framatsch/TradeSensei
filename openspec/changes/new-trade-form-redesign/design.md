## Context

`TradeForm.tsx` is a 835-line React Hook Form component that handles both "New Trade" creation and trade editing in a single component controlled by `isEditing`. The form currently contains:

- A currency text input that should be account-derived
- An Advanced Mode toggle with no enforced relationship to the COMBO checkbox
- Manually editable timestamps regardless of Advanced Mode state
- A "Tags & Playbook" section using the legacy `useTags` / `usePlaybooks` hooks
- A plain `<input type="file">` for image uploads

The 2x2 metadata architecture (Taxonomies + Annotations) is already fully implemented in the backend and has dedicated frontend hooks (`useTaxonomies`, `useAnnotationDefinitions`). A `ScreenshotUploader` drag-and-drop component already exists in `components/checkin/ScreenshotUploader.tsx` but is tightly coupled to the checkin upload URL endpoint.

**Key API constraint**: `TradeCreateRequest` does not accept `taxonomy_ids` or `annotation_ids`. Taxonomy and annotation assignment requires separate POST calls to `/api/v1/trades/{id}/taxonomies` and `/api/v1/trades/{id}/annotations/{definition_id}` after the trade is created.

## Goals / Non-Goals

**Goals:**
- Enforce COMBO → Advanced Mode hard-lock in state and UI
- Auto-derive `opened_at` / `closed_at` from execution leg timestamps in Advanced Mode
- Replace Tags & Playbook panel with 2x2 metadata matrix (Taxonomies + Annotations)
- Replace `<input type="file">` with a drag-and-drop uploader zone
- Remove currency input; display account currency as read-only label
- Full-width form layout

**Non-Goals:**
- Backend API changes (no new fields on `TradeCreateRequest`)
- Metadata assignment on the edit form (out of scope for this change)
- Removing `tag_ids` / `playbook_id` from `TradeCreate` payload or API
- Refactoring `ScreenshotUploader` to be a fully generic shared component (adapt inline)

## Decisions

### Decision 1: Two-step trade creation for metadata assignment

**Problem**: `TradeCreateRequest` has no `taxonomy_ids` or `annotation_value` fields. Taxonomies/Annotations are assigned via separate endpoints post-creation.

**Decision**: After `createMutation.mutate()` resolves successfully, fire the taxonomy/annotation assignment mutations in parallel before navigating. The user sees a single "Creating..." state.

**Alternatives considered**:
- Add `taxonomy_ids` to `TradeCreateRequest` in the backend — rejected (out of scope, requires backend + migration changes).
- Assign metadata before navigation in `onSuccess` callback — accepted; simpler, no UI changes needed beyond loading state.

**Risk**: If the trade creation succeeds but a metadata assignment fails, the trade exists without the intended metadata. Mitigation: show a non-blocking warning toast; the user can assign metadata from the trade detail page.

---

### Decision 2: Adapt ScreenshotUploader rather than extract a shared component

**Problem**: `ScreenshotUploader` uses the checkin-specific upload URL endpoint. The trade form needs the trade image upload endpoint.

**Decision**: Introduce a `TradeScreenshotUploader` component (or a prop-based upload URL factory) that mirrors the drag-and-drop UI of `ScreenshotUploader` but uses `useTradeImageUploadUrl`. Do not refactor `ScreenshotUploader` itself.

**Alternatives considered**:
- Extract a fully generic `DragDropUploader` — good long-term but out of scope.
- Pass an upload URL generator as a prop to `ScreenshotUploader` — feasible but modifies a component outside this change's blast radius.

---

### Decision 3: Zod schema refine update for COMBO + Advanced Mode

**Current state**: The `createSchema` refines check `is_combo ? true : ...` for quantity and entry_price, but there is no condition for Advanced Mode. When both COMBO and Advanced Mode are forced on, no leg-derived values are required by the schema (the form allows zero legs).

**Decision**: Add a refine: when `isAdvancedMode === true`, require at least 1 execution leg. Keep existing COMBO bypasses. This prevents empty Advanced Mode submissions.

---

### Decision 4: Timestamp auto-sync via `useEffect`

**Decision**: Extend the existing `useEffect` (which currently computes entry_price/qty from legs) to also call `setValue("opened_at", ...)` and `setValue("closed_at", ...)` with min/max `executed_at` values when `isAdvancedMode === true`. The fields are rendered as `disabled` in this mode.

---

### Decision 5: Scope filter for 2x2 queries

The proposal does not mention this, but Taxonomies and AnnotationDefinitions have a `scope` field (`trades`, `checkins`, `both`). The new Trade Taxonomies panel must call `useGetTaxonomies("trades")` and `useGetAnnotationDefinitions("trades")` to avoid showing checkin-only metadata.

## Wireframe Reference

```
+--------------------------------------------------------------------------------------+
| NEW TRADE | Account: Live Portfolio — USD (read-only)                                |
+--------------------------------------------------------------------------------------+
| INSTRUMENT & CORE SETTINGS                                                           |
| Symbol: [AAPL]   Direction: [LONG/SHORT]   [x] COMBO Position (locks Advanced Mode)  |
| Asset Class: [EQUITY]  (hidden when COMBO)                                           |
+--------------------------------------------------------------------------------------+
| EXECUTION MODE: [x] Advanced Mode (Manual Legs) [disabled if COMBO]                  |
|                                                                                      |
| [Table: Execution Legs]                                           [+ Add Leg]        |
| Date/Time (UTC)   Side     Qty      Price     Fees      Actions                      |
| [10.05.2026]      [Buy]    [25]     [150.20]  [1.00]    [🗑]                          |
+--------------------------------------------------------------------------------------+
| ENTRY / EXIT SUMMARY (auto-computed when Advanced Mode is ON)                        |
| Total Qty: [25]        Entry Price: [150.20]   Stop Loss:   [145.00]                 |
| Commission: [1.00]     Exit Price:  [155.00]   Take Profit: [160.00]                 |
| Opened At: [auto]  Closed At: [auto]   (disabled inputs when Advanced Mode)         |
+--------------------------------------------------------------------------------------+
| QUALITATIVE DATA (2x2 Matrix)                                                        |
|                                                                                      |
| Trade Taxonomies (Tags)              Trade Annotations (Variables)                   |
| [Multi-select: Select Taxonomies]    [Typed inputs per definition type]              |
|                                                                                      |
| Notes                                                                                |
| [Trade rationale, emotional state...]                                                |
+--------------------------------------------------------------------------------------+
| SCREENSHOTS                                                                          |
| [Drag & Drop zone — click or drop images here]                                       |
+--------------------------------------------------------------------------------------+
|                                                              [ CREATE TRADE ]        |
+--------------------------------------------------------------------------------------+
```

## Risks / Trade-offs

- **Two-step creation failure**: Trade is created but metadata not assigned → mitigated by error toast with link to trade detail.
- **Legacy `tag_ids` / `playbook_id` fields**: Removing from the create form means new trades created through the UI cannot have playbooks at creation time. This is acceptable since the trade detail edit form retains the Playbook field. Document in CHANGELOG.
- **COMBO + 0 legs validation**: Without a minimum-legs refine, a user can submit a COMBO + Advanced Mode trade with no legs and no aggregate data — must be caught in schema.
- **`toISOWithOffset` treats local time as UTC**: Pre-existing bug — out of scope but documented. The label "UTC" on the timestamp section is misleading.

## Open Questions

1. Should `playbook_id` be retained as a hidden/optional field in the create payload (submitted as `null`) for API backwards compatibility, or removed entirely from `TradeCreate`? **Proposed answer**: Keep in payload as `null`, just remove from UI. No API change needed.
2. Should the user rating field (1-5) stay in the Notes section or move to the Qualitative Data section? **Proposed answer**: Keep in Notes section — unrelated to 2x2 matrix.
