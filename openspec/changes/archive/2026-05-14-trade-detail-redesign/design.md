## Context

The Trade Detail page (`frontend/app/dashboard/trades/[id]/page.tsx`) was built incrementally across multiple iterations. The backend metadata system (taxonomies + annotations with typed columns) was completed in Iteration 6, but the frontend never wired it up. The page currently renders a "Playbook & Psychology" card with flat tags and a playbook dropdown — both are conceptually superseded by the new taxonomy/annotation system for trade qualitative data.

The two-column grid layout embeds the `ExecutionLegsTable` inside the left column, causing horizontal scrolling on wide tables. The `TradeImageGallery` component renders a static image gallery below the execution summary, which is redundant because `MediaChartsCard` already offers a Screenshots tab with full upload/management capability.

All required backend endpoints and frontend hooks already exist:
- `useTradeMetadata` — assign/remove/update taxonomies and annotations
- `useTaxonomies` — list taxonomy definitions (filterable by scope)
- `useAnnotationDefinitions` — list annotation definitions with typed metadata

## Goals / Non-Goals

**Goals:**
- Render trade taxonomies and annotations on the Trade Detail page with editable UI
- Implement dynamic annotation input rendering based on definition `data_type` (`int`/`float` → number input with range validation, `bool` → toggle, `string_enum` → dropdown)
- Restructure the page layout to follow the wireframe: chart+performance row → qualitative metadata section → execution legs table
- Remove the flat Tags and Playbook inline components from this page
- Remove the redundant `TradeImageGallery` block from the page
- Move Stop Loss / Take Profit to the top of the Performance card

**Non-Goals:**
- Removing the Tags system from other pages (trade list, reports)
- Removing the Playbook field from the trade data model or API
- Modifying the backend in any way
- Changing the `ExecutionSummaryCard` content or behavior
- Adding check-in annotations or taxonomies to this page

## Decisions

### D1: New `QualitativeMetadataPanel` component (not inline in `page.tsx`)
The current page already has three large inline components (`InlineNumberField`, `InlinePlaybookField`, `InlineTagsField`). Adding another large section inline would make `page.tsx` unmanageable. Extracting to `components/trades/QualitativeMetadataPanel.tsx` keeps the page file as a layout orchestrator and makes the panel independently testable.

**Alternative considered**: Keep inline in page.tsx — rejected because the panel manages its own edit state, draft state, and 3 API mutation hooks. That logic does not belong in a page-level component.

### D2: Separate `AnnotationInput` component for dynamic type rendering
The typed input rendering logic (`int`/`float`/`bool`/`string_enum`) is a non-trivial switch. A dedicated `AnnotationInput.tsx` component isolates this rendering concern, enables independent testing, and can be reused if a similar UI is needed for check-in annotations later.

### D3: Edit mode is card-scoped (not field-inline)
Per the wireframe, the Qualitative Analysis section has a single `[✎ Edit]` button in the card header. Clicking it opens the entire section for editing. The "Save" button writes all three concerns (taxonomies, annotations, notes) in the appropriate API calls. This matches the Performance card's existing edit pattern (`InlineNumberField` with per-field save). 

**Alternative considered**: Auto-save on blur — rejected because annotations require validation (range check, enum membership) that is better surfaced before committing.

### D4: `useTaxonomies` and `useAnnotationDefinitions` filtered by `scope=trades`
Both hooks accept an optional `scope` query parameter. We pass `scope=trades` to avoid showing check-in-only definitions on this page. The hook call happens at the panel level so that the definition lists are fetched once and passed to each row renderer.

### D5: Preserve Playbook field — move it into QualitativeMetadataPanel
The Playbook field still has value for users who configured playbooks. Rather than removing it, it is moved into the Qualitative Analysis panel alongside the new taxonomy/annotation inputs. This reduces disruption for existing users while co-locating all qualitative metadata in one place.

**Alternative considered**: Remove Playbook from the page entirely — rejected because it requires a more invasive data migration discussion and user communication.

## Risks / Trade-offs

- **[Risk] Trade response may not always embed taxonomies/annotations** → The `Trade` type marks these as optional (`taxonomies?`, `annotations?`). Mitigation: treat missing arrays as empty arrays; no conditional rendering guard needed beyond `?? []`.
- **[Risk] String enum dropdown options can be empty** → If `scale_labels.options` is null or empty for a `string_enum` annotation definition, the dropdown would render empty. Mitigation: `AnnotationInput` renders a disabled placeholder "No options defined" in this case.
- **[Risk] Performance card layout shift when SL/TP move to top** → Users accustomed to SL/TP at the bottom will find them at the top. Mitigation: this is a deliberate wireframe decision; no technical risk.
- **[Risk] Removing `useTags` and `usePlaybooks` from the page may surprise users** → The old flat tag picker disappears. Mitigation: covered in proposal; tags are superseded by taxonomies.
