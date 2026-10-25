/*
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import { test, expect } from '@playwright/test';

test.describe('Chart Cache Refresh', () => {
  let fetchCount = 0;

  test.beforeEach(async ({ page }) => {
    fetchCount = 0;

    // Intercept the API call before navigating so the initial chart load succeeds
    // and does not fall back to the TradingView widget when Market Data Hub is offline.
    await page.route('**/api/v1/market-data/prices/*/history*', async (route) => {
      const url = new URL(route.request().url());
      if (url.searchParams.get('force_refresh') === 'true') {
        fetchCount++;
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: [
            {
              start: "2023-10-01T00:00:00Z",
              open: 150,
              high: 155,
              low: 149,
              close: 154,
              volume: 10000
            }
          ]
        })
      });
    });

    // Navigate to a trade detail page where TradeChart is rendered
    await page.goto('/dashboard/trades');

    // Wait for trades to load and click the first trade symbol link
    const firstTradeLink = page.locator('tbody tr a').first();
    await firstTradeLink.waitFor({ state: 'visible' });
    await firstTradeLink.click();

    // Wait for the chart component to be visible
    await page.waitForSelector('button[title="Refresh"]');
  });

  test('Refresh button triggers data reload', async ({ page }) => {
    const refreshButton = page.locator('button[title="Refresh"]');
    await refreshButton.click();

    // Verify the API was called with force_refresh=true
    await expect.poll(() => fetchCount).toBe(1);
  });
});
