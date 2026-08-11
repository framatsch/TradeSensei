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

test.describe('Workspace Navigation', () => {
  test.beforeEach(async ({ page }) => {
    // Clear localStorage to prevent WorkspaceFilterContext from redirecting and cancelling our navigations
    await page.goto('/dashboard/workspace/overview');
    await page.evaluate(() => window.localStorage.clear());
    await page.goto('/dashboard/workspace/overview');
    await expect(page.getByText('Portfolio Workspace', { exact: true }).first()).toBeVisible({ timeout: 15_000 });
  });

  const routes = [
    { path: '/dashboard/workspace/overview', name: 'Overview' },
    { path: '/dashboard/workspace/calendar', name: 'Calendar' },
    { path: '/dashboard/workspace/reporting', name: 'Reporting' },
    { path: '/dashboard/workspace/performance/strategy', name: 'Strategy' },
    { path: '/dashboard/workspace/performance/behavior', name: 'Behavior' }
  ];

  for (const route of routes) {
    test(`can navigate to ${route.name} and verify active state`, async ({ page }) => {
      // Click the sidebar link
      const link = page.getByRole('link', { name: route.name }).first();
      await expect(link).toBeVisible();
      await link.click();

      // Verify URL
      await expect(page).toHaveURL(new RegExp(route.path));

      // Verify active state
      await expect(link).toHaveClass(/nav-active/);
    });
  }
});
