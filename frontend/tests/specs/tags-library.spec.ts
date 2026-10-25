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

test.describe('Tags (Taxonomies) Library', () => {
  test.describe.configure({ mode: 'serial' });

  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard/library/tags');
    await page.waitForLoadState('networkidle');
  });

  test('TC-100 navigate to tags page and see the list', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Tags' })).toBeVisible();
    await expect(page.getByText('Manage reusable metadata taxonomies')).toBeVisible();
    
    // The list should be visible (seeded in global-setup.ts)
    await expect(page.getByRole('heading', { name: 'high-conviction', exact: true })).toBeVisible();
  });

  test('TC-101 create a new tag', async ({ page }) => {
    // 1. Click "New Tag"
    await page.getByRole('button', { name: 'New Tag' }).click();
    
    // 2. Fill form (Scope defaults to Trades)
    await page.getByLabel('Tag name').fill('E2E Test Tag');
    await page.getByRole('textbox', { name: 'Tag description' }).fill('A tag created by E2E test');
    
    // Pick a color (second color button)
    const colorButtons = page.locator('button[aria-label^="color #"]');
    await colorButtons.nth(1).click();
    
    // 3. Save
    await page.getByRole('button', { name: 'Save' }).click();
    
    // 4. Verify in list
    await expect(page.getByRole('heading', { name: 'E2E Test Tag' })).toBeVisible();
  });

  test('TC-102 edit an existing tag', async ({ page }) => {
    // Click the Edit icon
    await page.getByRole('button', { name: 'Edit E2E Test Tag' }).click();
    
    // Modify
    await page.getByLabel('Tag name').fill('E2E Edited Tag');
    await page.getByRole('button', { name: 'Save' }).click();
    
    // Verify
    await expect(page.getByRole('heading', { name: 'E2E Edited Tag' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'E2E Test Tag' })).not.toBeVisible();
  });

  test('TC-103 delete a tag', async ({ page }) => {
    // Click Delete icon
    await page.getByRole('button', { name: 'Delete E2E Edited Tag' }).click();
    
    // Confirm delete in the inline confirmation banner after async assignment count loads
    await expect(page.getByText(/Are you sure you want to delete tag/i)).toBeVisible({ timeout: 10_000 });
    await page.getByRole('button', { name: 'Delete', exact: true }).last().click();
    
    // Verify removal
    await expect(page.getByRole('heading', { name: 'E2E Edited Tag' })).not.toBeVisible({ timeout: 10_000 });
  });
});
