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

// Run unauthenticated so we can test the register flow
test.use({ storageState: { cookies: [], origins: [] } });

test.describe('Default Metadata Seed on Registration', () => {
  test('TC-140 new user gets default tags and metrics automatically', async ({ page }) => {
    // Generate a unique username and email
    const uniqueId = Date.now().toString();
    const username = `new_user_${uniqueId}`;
    const email = `new_user_${uniqueId}@example.com`;
    const password = 'TestPassword123!';

    // 1. Go to register page
    await page.goto('/register');
    
    // 2. Fill the registration form
    await page.getByLabel('Username').fill(username);
    await page.getByLabel('Email').fill(email);
    await page.getByLabel('Password', { exact: true }).fill(password);
    await page.getByLabel('Confirm Password', { exact: true }).fill(password);
    
    // 3. Submit
    await page.getByRole('button', { name: 'Create Account' }).click();
    
    // 4. Verify successful redirection to dashboard
    await expect(page).toHaveURL(/\/dashboard/);
    
    // 5. Navigate to Tags (Taxonomies) and check defaults
    await page.goto('/dashboard/library/tags');
    
    // Expected default tags
    await expect(page.getByRole('heading', { name: 'FOMO' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Breakout' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Trend Following' })).toBeVisible();
    
    // 6. Navigate to Metrics (Annotations) and check defaults
    await page.goto('/dashboard/library/metrics');
    
    // Expected default metrics
    await expect(page.getByRole('heading', { name: 'Mood Level' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Rule Followed' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Setup Quality' })).toBeVisible();
  });
});
