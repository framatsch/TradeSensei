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

test.describe('Metrics (Annotations) Library', () => {
  test.describe.configure({ mode: 'serial' });

  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard/library/metrics');
    await page.waitForLoadState('networkidle');
  });

  test('TC-110 navigate to metrics page and see the list', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Metrics' })).toBeVisible();
    await expect(page.getByText('Manage reusable annotation definitions')).toBeVisible();
    
    // The metrics list should have at least the seeded Focus metric
    await expect(page.getByRole('heading', { name: 'Focus' })).toBeVisible();
  });

  test('TC-111 create a new metric (int)', async ({ page }) => {
    // 1. Click "New Metric"
    await page.getByRole('button', { name: 'New Metric' }).click();
    
    // 2. Fill form
    await page.locator('input').first().fill('E2E Conviction');
    await page.locator('select').nth(0).selectOption('int');

    await page.getByPlaceholder('Optional description...').fill('E2E Test Metric');
    
    // Scale labels
    await page.locator('input[type="number"]').nth(0).fill('1');
    await page.locator('input[type="number"]').nth(1).fill('10');
    
    // 3. Save
    await page.getByRole('button', { name: 'Save', exact: true }).click();
    
    // 4. Verify in list
    await expect(page.getByRole('heading', { name: 'E2E Conviction', exact: true })).toBeVisible();
  });

  test('TC-112 edit an existing metric', async ({ page }) => {
    // Click the Edit icon
    await page.getByRole('button', { name: 'Edit E2E Conviction', exact: true }).click();
    
    // Modify
    await page.locator('input').first().fill('E2E Conviction Edited');
    await page.getByRole('button', { name: 'Save', exact: true }).click();
    
    // Verify
    await expect(page.getByRole('heading', { name: 'E2E Conviction Edited' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'E2E Conviction', exact: true })).not.toBeVisible();
  });

  test('TC-113 create a new metric (string enum)', async ({ page }) => {
    await page.getByRole('button', { name: 'New Metric' }).click();
    
    await page.locator('input').first().fill('E2E Setup Quality');
    await page.locator('select').nth(0).selectOption('string_enum');
    
    // Option 1 is already there, fill it
    await page.getByPlaceholder('Option 1').fill('A+');
    
    // Add Option 2
    await page.getByRole('button', { name: 'Add option' }).click();
    await page.getByPlaceholder('Option 2').fill('B');
    
    // Save
    await page.getByRole('button', { name: 'Save', exact: true }).click();
    
    await expect(page.getByRole('heading', { name: 'E2E Setup Quality' })).toBeVisible();
  });

  test('TC-114 delete metrics', async ({ page }) => {
    // Delete first metric
    await page.getByRole('button', { name: 'Delete E2E Conviction Edited', exact: true }).click();
    await expect(page.getByText('Are you sure you want to delete metric')).toBeVisible();
    await page.getByRole('button', { name: 'Delete', exact: true }).last().click();
    await expect(page.getByRole('heading', { name: 'E2E Conviction Edited', exact: true })).not.toBeVisible();

    // Delete second metric
    await page.getByRole('button', { name: 'Delete E2E Setup Quality', exact: true }).click();
    await expect(page.getByText('Are you sure you want to delete metric')).toBeVisible();
    await page.getByRole('button', { name: 'Delete', exact: true }).last().click();
    await expect(page.getByRole('heading', { name: 'E2E Setup Quality', exact: true })).not.toBeVisible();
  });
});
