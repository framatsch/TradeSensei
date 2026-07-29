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
  test.beforeEach(async ({ page }) => {
    // Navigate to a trade detail page where TradeChart is rendered
    // Using a mocked trade or clicking into the first trade in the dashboard
    await page.goto('/dashboard/trades');
    
    // Wait for trades to load and click the first one
    const firstTrade = page.locator('tbody tr').first();
    await firstTrade.waitFor({ state: 'visible' });
    await firstTrade.click();
    
    // Wait for the chart component to be visible
    await page.waitForSelector('button[title="Force Refresh Data"]');
  });

  test('Refresh button triggers data reload', async ({ page }) => {
    // Intercept the API call to mock the response
    let fetchCount = 0;
    await page.route('**/api/v1/market-data/prices/*/history?*', async (route) => {
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

    const refreshButton = page.locator('button[title="Force Refresh Data"]');
    await refreshButton.click();

    // Verify the button spins or we can just verify the API was called
    expect(fetchCount).toBe(1);
  });
});
