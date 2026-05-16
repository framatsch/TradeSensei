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

/**
 * Reports Navigation Spec
 */

import { test, expect } from '@playwright/test';

test.describe('Performance Reports — Navigation', () => {
  test('TC-R007 Calendar report day click navigates to trades with date filters', async ({ page }) => {
    await page.goto('/dashboard/workspace/calendar');
    await expect(page.getByRole("link", { name: "Calendar" }).first()).toBeVisible({ timeout: 15_000 });
    
    // Wait for the spinner to disappear so calendar data is loaded
    await expect(page.locator('.animate-spin')).toHaveCount(0, { timeout: 10_000 });
    await page.waitForTimeout(1000); // Give it a moment to paint the calendar days

    // The calendar defaults to the current month, which might not have trades if seeded 5-60 days ago.
    // Let's click "Previous" a couple of times if needed until we find a day with trades.
    for (let i = 0; i < 3; i++) {
      const count = await page.locator('div.cursor-pointer', { hasText: /trades/i }).count();
      if (count > 0) {
        break;
      }
      await page.getByRole('button', { name: 'Previous' }).click();
      // Small wait to let it rerender
      await page.waitForTimeout(1000);
    }

    const dayWithTrades = page.locator('div.cursor-pointer', { hasText: /trades/i }).first();
    await expect(dayWithTrades).toBeVisible({ timeout: 15_000 });

    await dayWithTrades.click();

    // Verify it navigated to the trades page with date query params
    await expect(page).toHaveURL(/\/dashboard\/trades/, { timeout: 8_000 });
    await expect(page).toHaveURL(/date_from=/);
    await expect(page).toHaveURL(/date_to=/);
  });
});








