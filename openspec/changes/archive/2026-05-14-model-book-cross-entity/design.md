## Context

The current Model Book is a check-in screenshot gallery (`ModelBookView.tsx`) driven by the existing `GET /checkins` endpoint. It has no concept of "starred" items — it shows *all* check-ins with screenshots. The issue requests a paradigm shift: explicit starring on both trades and check-ins, and a unified cross-entity gallery.

**Current state:**
- `trades` and `daily_checkins` tables have no `is_modelbook` column.
- `ModelBookView` renders all check-in entries with screenshots, not starred ones.
- `trade-detail-redesign` change is open (0/21 tasks done) — the trade detail toolbar is actively in flux.
- `checkin-modelbook-filters` spec already defines the filter bar for check-ins.

**Constraints:**
- All monetary values must use `Decimal`, not `float`.
- All timestamps are UTC timezone-aware.
- Frontend must not use raw `fetch()` — API client only.
- No `dark:` Tailwind modifiers — semantic tokens only.

## Goals / Non-Goals

**Goals:**
- Add `is_modelbook` boolean to `trades` and `daily_checkins` with Alembic migration.
- PATCH endpoints to toggle starring on each entity.
- New aggregated GET endpoint returning merged, date-sorted starred entries with pagination.
- Replace `ModelBookView` with a cross-entity grid supporting Trade and Check-in cards.
- Star toggle on Trade Detail toolbar and Check-in form toolbar.
- Entity-type filter in the Model Book filter bar (All / Trades / Check-ins).

**Non-Goals:**
- Real-time WebSocket updates for starring state.
- Bulk-starring multiple items at once.
- Reordering/pinning cards within the Model Book (starred items are always date-sorted).
- A separate "Model Book" top-level route — it remains a view tab within `/dashboard/checkins`.

## Decisions

### D1: Aggregated backend endpoint vs. client-side merge

**Decision:** Implement a dedicated `GET /model-book/entries` endpoint that queries both tables and returns a unified sorted list with pagination, rather than making two parallel frontend requests and merging client-side.

**Rationale:** Client-side merge is fragile with pagination — merging page 1 of trades and page 1 of check-ins by date does not yield a correct sorted page. Server-side merge with `UNION ALL` + `ORDER BY date DESC` + keyset pagination is the only correct approach.

**Alternative considered:** Two parallel requests + client-side merge per page. Rejected because pagination semantics break — page 2 of a merged stream cannot be deterministically computed from separate cursors.

**Note:** The issue mentions "a unified API endpoint (or a BFF aggregator)" — the BFF aggregator option is incorrect for a paginated sorted stream for the reason above.

### D2: PATCH vs. PUT for star toggle

**Decision:** Use `PATCH /trades/{id}/modelbook` and `PATCH /checkins/{date}/modelbook` with a body `{"is_modelbook": bool}` rather than separate POST/DELETE star endpoints.

**Rationale:** Idempotent PATCH is consistent with the project's existing patterns (e.g., similar PATCH operations on other resources). No state machine complexity needed — it's just a boolean flip.

### D3: Trade Detail star toggle — coordination with `trade-detail-redesign`

**Decision:** Add the star toggle to the Trade Detail page as a standalone icon button in the existing toolbar area, but do *not* redesign the toolbar layout. The `trade-detail-redesign` change will own the full redesign; this change inserts only the star button.

**Rationale:** `trade-detail-redesign` has 0/21 tasks done and is not blocked on this. Waiting would indefinitely delay Model Book. A surgical insertion is safe; the redesign can relocate the button later.

**Risk:** Merge conflict if `trade-detail-redesign` is implemented simultaneously. Mitigation: document the star button placement in both changes; coordinate before merging.

### D4: ModelBook entry response shape

**Decision:** The `GET /model-book/entries` response returns a discriminated union list:

```json
{
  "items": [
    {"type": "trade", "id": "...", "date": "...", "symbol": "...", "result_r": 2.4, "image_urls": [...], "tags": [...] },
    {"type": "checkin", "date": "...", "market_phase": "...", "screenshot_urls": [...], "regime_color": "..." }
  ],
  "total": 42,
  "next_cursor": "..."
}
```

The `type` discriminator enables the frontend to render the correct card variant without further lookups.

### D5: Filter bar evolution

**Decision:** Extend `ModelBookFilterBar` to add an entity-type toggle (All / Trades / Check-ins). When "Trades" is selected, the regime/phase filter is hidden. When "Check-ins" is selected, a tag filter is hidden. The `GET /model-book/entries` endpoint accepts an optional `entity_type` query param (`trade` | `checkin`).

## Risks / Trade-offs

- **[Risk] Pagination cursor complexity** — `UNION ALL` queries with keyset pagination require a composite cursor (entity_type + date + id). The cursor must be opaque (base64-encoded JSON) to avoid leaking implementation. → Mitigation: Use offset pagination initially (simpler), upgrade to cursor if performance requires.
- **[Risk] `trade-detail-redesign` conflict** — Star button placement may conflict. → Mitigation: Coordinate; the redesign change should preserve any existing toolbar buttons.
- **[Risk] Current `ModelBookView` behavior changes** — Existing users see all check-ins with screenshots; after this change, they only see starred items. This is a deliberate UX shift aligned with the issue, but may surprise existing users. → Mitigation: Document in changelog.
- **[Trade-off] Offset vs. cursor pagination** — Offset is simpler but degrades at scale. For a personal trading journal, total starred items will rarely exceed hundreds. Offset is acceptable.

## Migration Plan

1. Write Alembic migration adding `is_modelbook` (default `false`) to both tables.
2. Existing rows default to `false` — no data migration needed.
3. Deploy backend; existing endpoints unchanged.
4. Deploy frontend; `ModelBookView` replaces silently (users had no starred items yet, gallery appears empty with a clear CTA).
5. Rollback: remove `is_modelbook` columns (safe — boolean default, no data dependency).

## Open Questions

- **OQ1:** Should starring a trade also work when the trade has no `image_urls`? The issue shows image previews in all cards — if a trade has no images, should it still be star-able? *Assumption: yes — the image slot renders a placeholder.*
- **OQ2:** The issue mockup shows "Metrics (Advanced)" as a filter. This is not further specified. Deferred to a follow-up; not in scope for this change.
- **OQ3:** The `checkin-modelbook-filters` spec defines a "regime" filter. Should this be renamed to "market phase" in the unified filter bar for clarity? *Assumption: keep "regime" label for now to match existing UI.*
