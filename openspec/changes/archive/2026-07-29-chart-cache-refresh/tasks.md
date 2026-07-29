## 1. Backend

- [x] 1.1 Add `DELETE /api/v1/market-data/cache` endpoint in `market_data.py`.
- [x] 1.2 Implement the DB clear logic in `market_data_service.py` to delete rows from `ohlc_prices` where the symbol matches any symbol traded by the current user. (Fetch user's traded symbols first).
- [x] 1.3 Add `force_refresh` boolean query param to `GET /prices/{symbol}/history` endpoint in `market_data.py`.
- [x] 1.4 Update the caching logic in `market_data.py` to bypass reading from cache if `force_refresh=true`.

## 2. Frontend

- [x] 2.1 Add a "Refresh" icon button in `TradeChart.tsx` adjacent to the "Options" button.
- [x] 2.2 Modify `fetchAndRender` in `TradeChart.tsx` to accept a boolean flag and pass `force_refresh=true` to the proxy API call (or ensure it's passed through to the backend endpoint).
- [x] 2.3 Update the frontend proxy in `route.ts` (if applicable) or backend integration to ensure `force_refresh` is forwarded properly.
- [x] 2.4 Add "Clear chart candles cache" button in Look & Feel settings tab.
- [x] 2.5 Add a confirmation dialog that asks "Are you sure? - Yes/No" when clicking the clear cache button.
- [x] 2.6 Connect the confirmation dialog's "Yes" action to call the proxy for `DELETE /api/v1/market-data/cache` and show a success toast.

## 3. Testing

- [x] 3.1 Write a mocked unit test for the `GET /api/v1/market-data/prices/{symbol}/history` endpoint to ensure `force_refresh=true` bypasses the cache.
- [x] 3.2 Write a mocked unit test for `DELETE /api/v1/market-data/cache` to ensure it only deletes the current user's symbols from the cache.
- [x] 3.3 Write an E2E test (via Selenium/Playwright) for the UI to verify the "Refresh" button click triggers a chart data reload. Use network interception (e.g., `page.route` in Playwright) to mock the API response so no real backend/MDH calls are made.

## 4. Code Review Fixes

- [x] 4.1 Fix `UnboundLocalError` in `market_data.py` by initializing `cached_bars = None`.
- [x] 4.2 Add manual audit logging for the cache clearing operation in `market_data.py`.
- [x] 4.3 Replace hardcoded red colors in `GeneralSettings.tsx` with semantic tokens (`bg-destructive/10`, `text-destructive`, `border-destructive/20`).
- [x] 4.4 Review/Document the shared cache deletion behavior in `market_data_service.py` to clarify it is intentional or modify it to avoid stampedes.
