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

test.describe('Checkin Metadata', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to Check-ins page
    await page.goto('/dashboard/checkins');
    // Wait for initial load
    await expect(page.getByRole('heading', { name: 'Check-ins', exact: true })).toBeVisible({ timeout: 15_000 });
  });

  test('TC-300 check-in form contains Tags and Annotations sections', async ({ page }) => {
    // Click "Today's Check-in" to open the form
    await page.getByRole('link', { name: /Today's Check-in/i }).click();
    
    // Wait for form to load
    await expect(page.getByRole('button', { name: 'Save', exact: true })).toBeVisible({ timeout: 10_000 });

    // Verify sections are visible
    await expect(page.getByText('Tags', { exact: true })).toBeVisible();
    await expect(page.getByText('Annotations', { exact: true })).toBeVisible();
  });

  test('TC-301 check-in filter bar contains Tags and Annotation Filters', async ({ page }) => {
    // Click the Filters toggle to expand
    const filterToggle = page.getByRole('button', { name: /Filters/i });
    await filterToggle.click();

    // Verify expanded panel labels
    await expect(page.getByText('Tags', { exact: true })).toBeVisible();
    await expect(page.getByText('Annotation Filters', { exact: true })).toBeVisible();
    
    // Check for the "Add" button in AnnotationFilterRows
    await expect(page.getByRole('button', { name: /Add/i })).toBeVisible();
  });
});
