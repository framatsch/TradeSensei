## Context

The daily check-in feature requires market context. A previous proposal suggested embedding dynamic OHLC charts for a single index. This was rejected due to two architectural vetoes:
1. **Anti-Lag / No Embedded Charts**: Dynamic charts in a timeline list block the main thread and degrade performance. Furthermore, they destroy historical context by showing raw candles instead of the user's manual drawings from that specific day.
2. **No Single-Index Limitation**: Traders track multiple indices simultaneously (e.g., watching both NDX and SPX for divergence). Forcing one index per check-in fragments the database and UI.

## Goals / Non-Goals

**Goals:**
- Allow users to manage a list of market indices via settings.
- Allow associating *multiple* market indices with a single daily check-in.
- Render selected indices as lightweight badges and external TradingView links in the UI.
- Rely exclusively on static screenshots for visual chart evidence.

**Non-Goals:**
- Embedding or fetching any live or cached OHLC data for indices.
- Complex or dynamic chart rendering components within the timeline.

## Decisions

### 1. Multi-Select Data Model
We will use a `market_index_definitions` table for configuration, and a `checkin_market_indices` junction table to support a many-to-many relationship between check-ins and indices.
*Rationale*: Supports tagging multiple indices (e.g., SPX and NDX) on a single day without denormalizing data into a simple string array.

### 2. Static Visual Evidence ONLY
Visual chart data for indices MUST ONLY be provided via static image uploads saved to the `screenshot_urls` array.
*Rationale*: Ensures UI performance in list views (Anti-Lag) and preserves exact historical annotations drawn by the user on that day.

### 3. API Payload
The `DailyCheckinPayload` (used for Create and Update actions) will accept an array of UUIDs: `target_index_ids: list[UUID]`.

## Risks / Trade-offs

- **Trade-off:** Users must manually capture and upload screenshots if they want visual charts.
  - *Mitigation:* This is a deliberate architectural trade-off favoring rendering performance and historical accuracy over convenience.

## Migration Plan

1. **Database Migration:** Create the Alembic revision for `market_index_definitions` and the `checkin_market_indices` junction table.
2. **Backend API:** Implement CRUD endpoints for index definitions. Update check-in services to handle junction table sync for `target_index_ids`.
3. **Frontend UI:** Implement the Settings page for indices. Update the Check-in Form to use a multi-select component. Render static badges and external links in views.
4. **Testing:** Update backend and E2E tests to verify many-to-many behavior and static rendering.