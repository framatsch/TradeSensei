# Security + UI Verification — Round 6

Reviewer: Senior Code Reviewer (claude-sonnet-4-6)
Date: 2026-06-06

---

## Verified ✅

### 1. Audit log — `exception_message` + `stack_trace` removed
**File**: `backend/app/core/audit_middleware.py` — `_log_exception` method (lines 350–379)

Both `exception_message` and `stack_trace` keys are gone. The metadata dict now contains only:
```python
metadata={"exception_type": type(exc).__name__}
```
✅ Fix is correct and complete.

---

### 3. `operator: Literal[...]` prevents injection surface
**File**: `backend/app/schemas/annotation_filter.py` — line 40

```python
operator: Literal["eq", "neq", "lt", "lte", "gt", "gte"] = Field(...)
```
✅ Literal constraint is present. Invalid operator strings are rejected at the Pydantic validation boundary before reaching `_operator_expr`.

---

### 4. `orange-500` → `warning` token
**File**: `frontend/components/ui/AnnotationFilterRows.tsx` — lines 212–214

```tsx
? "bg-warning/15 border-warning/40 text-warning"
```
✅ `orange-500` is gone; `warning` semantic token is used.

**`--warning` CSS variable exists**: confirmed in both `:root` (line 45) and `.dark` (line 75) of `frontend/app/globals.css`:
```css
--warning: #f59e0b;   /* amber-500 */
```
The `warning` token is also registered in `tailwind.config.ts` (lines 64–67):
```ts
warning: {
  DEFAULT: "var(--warning)",
  foreground: "var(--warning-foreground)",
},
```
✅ Token is fully wired — both light and dark modes.

---

### 7. `RegimePills` null guard on `color_hex`
**File**: `frontend/components/checkin/RegimePills.tsx` — lines 52–53

```tsx
style={{
  borderColor: isActive ? (phase.color_hex ?? "var(--border)") : `${phase.color_hex ?? "var(--border)"}40`,
}}
```
✅ Null guard `?? "var(--border)"` is present in both the active and inactive branches. The `"undefined40"` bug is fixed.

---

## Issues Found

### [BLOCKER] Audit middleware verb mismatch — `PATCH` override but endpoint uses `PUT`
**File**: `backend/app/core/audit_middleware.py` — line 46  
**Cross-reference**: `backend/app/api/v1/saved_checkin_filters.py` — line 81

The wildcard override table registers:
```python
("PATCH", "/api/v1/checkins/filters/"): ("checkin_filter.updated", "checkin_filter"),
```
But the actual update endpoint is declared as:
```python
@router.put("/{filter_id}", ...)
async def update_saved_checkin_filter(...)
```
`PUT` requests to `/api/v1/checkins/filters/<id>` will **not** match the wildcard override (which requires `PATCH`). They will fall through to the generic `_RESOURCE_PATTERN` path, which strips the trailing `s` from `filters` and infers action `filter.updated` — a different resource name than the intended `checkin_filter.updated`. The audit log for every filter update is silently mis-labelled.

**Recommendation**: Either change the override key to `("PUT", "/api/v1/checkins/filters/")`, or change the endpoint decorator to `@router.patch(...)` and update the schema/client accordingly. The former is the lower-risk fix since it requires no API contract change.

---

### [SHOULD FIX] Dead import — `traceback` imported but never used
**File**: `backend/app/core/audit_middleware.py` — line 20

```python
import traceback
```
`traceback` was presumably used when `stack_trace` was written to audit metadata. Now that the key is removed, the import is dead. `mypy --strict` / `ruff` will flag this as an unused import.

**Recommendation**: Remove `import traceback` from line 20.

---

### [SHOULD FIX] `text-white` hardcode on destructive confirm button
**File**: `frontend/components/checkin/CheckinFilterBar.tsx` — line 279

```tsx
className="px-2 py-0.5 bg-destructive text-white rounded hover:bg-destructive/90 transition-colors"
```
`text-white` is a hardcoded color. The design system rule (AGENTS.md §5) prohibits hardcoded colors; the correct semantic token is `text-destructive-foreground` (which resolves to `#ffffff` in both themes, but is theme-aware by contract).

**Recommendation**: Replace `text-white` with `text-destructive-foreground`.

---

### [SHOULD FIX] `bg-white` on toggle thumb not replaced
**File**: `frontend/components/checkin/AnnotationEditor.tsx` — line 82

```tsx
<span
  className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform ${value ? "translate-x-4" : "translate-x-0.5"}`}
/>
```
Round 5 flagged `bg-white` on the toggle thumb. It is **still present**. On a dark background the white thumb is intentional for contrast, but the correct semantic token is `text-primary-foreground` (which is `#ffffff` in both themes). Using `bg-white` breaks the design system contract and will render incorrectly if `--primary-foreground` is ever changed.

**Recommendation**: Replace `bg-white` with `bg-primary-foreground`.

---

### [SHOULD FIX] Missing `aria-label` on `<select>` elements in `AnnotationFilterRows`
**File**: `frontend/components/ui/AnnotationFilterRows.tsx` — lines 83–91, 98–109, 223–235, 241–251

The only `aria-label` present in this file is on the "Remove filter" `<button>` (line 268). The three `<select>` elements inside `AnnotationValueInput` (bool, string_enum) and the two `<select>` elements in the chip row (definition selector, operator selector) have no `aria-label` or associated `<label>`. Screen readers will announce these as unlabelled controls.

**Recommendation**: Add `aria-label` to each `<select>`:
- Definition selector: `aria-label="Annotation field"`
- Operator selector: `aria-label="Operator"`
- Bool value selector: `aria-label={`Value for ${definition.name}`}`
- String enum value selector: same pattern

---

### [SHOULD FIX] Missing `aria-label` on `<select>` and `<input>` in `AnnotationEditor`
**File**: `frontend/components/checkin/AnnotationEditor.tsx` — lines 102–114, 132–144

The `aria-label` added in this round covers only the bool toggle `<button>` (line 79). The `<select>` for `string_enum` (lines 102–114) and the `<input type="number">` for int/float (lines 132–144) still have no `aria-label`.

**Recommendation**: Add `aria-label={`${definition.name} value`}` to both the `<select>` and `<input>` elements.

---

### [SHOULD FIX] Modal focus not returned on close — no `Dialog.Trigger` or `useRef`
**File**: `frontend/components/checkin/CheckinFilterBar.tsx` — lines 232–242 (Save View button), lines 257–268 (Rename button)

Both modals are opened via plain `<button>` elements that set state directly (`setShowSaveModal(true)`, `setShowRenameModal(true)`). Neither uses `<Dialog.Trigger asChild>` nor a `useRef`-based focus restoration pattern. When the modal closes, focus is dropped to `<body>` instead of returning to the triggering button, which breaks keyboard navigation.

**Recommendation**: Wrap each trigger button with `<Dialog.Trigger asChild>` inside the corresponding `<Dialog.Root>`, or move the `<Dialog.Root>` to wrap the trigger button and use `<Dialog.Trigger asChild>`. Example:
```tsx
<Dialog.Root open={showSaveModal} onOpenChange={setShowSaveModal}>
  <Dialog.Trigger asChild>
    <button type="button" className="...">
      <Save className="w-3.5 h-3.5" />
      Save View
    </button>
  </Dialog.Trigger>
  <Dialog.Portal>...</Dialog.Portal>
</Dialog.Root>
```

---

## What's Still Missing

| # | Item | Status |
|---|------|--------|
| 2 | Audit middleware verb mismatch (`PATCH` vs `PUT`) | ❌ Not fixed — override key is wrong |
| 5 | `bg-white` on toggle thumb in `AnnotationEditor.tsx` | ❌ Not fixed |
| 6 | `text-white` on destructive confirm button in `CheckinFilterBar.tsx` | ❌ Not fixed |
| 8 | `aria-label` on `<select>`/`<input>` in `AnnotationFilterRows` and `AnnotationEditor` | ⚠️ Partially fixed (toggle button only) |
| 9 | Modal focus management via `Dialog.Trigger` | ❌ Not fixed |
| — | Dead `import traceback` left behind after security fix | ❌ New issue introduced by the fix |
