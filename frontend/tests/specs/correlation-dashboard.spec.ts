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

test.describe('Metadata Correlation Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to Strategy Analysis (Correlation)
    await page.goto('/dashboard/workspace/performance/strategy');
    await page.waitForLoadState('networkidle');
  });

  test('TC-130 renders scatter widgets for correlation analysis', async ({ page }) => {
    // Both scatter charts should be loaded
    await expect(page.getByRole('heading', { name: /MAE \/ MFE/i })).toBeVisible();
    await expect(page.getByRole('heading', { name: /Duration vs P&L/i })).toBeVisible();
    
    // There shouldn't be an error message
    await expect(page.getByText('Failed to load strategy analysis data.')).not.toBeVisible();
  });
});
