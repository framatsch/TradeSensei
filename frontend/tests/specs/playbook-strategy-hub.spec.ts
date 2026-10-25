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

test.describe('Playbook Strategy Hub', () => {
  test.describe.configure({ mode: 'serial' });

  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard/library/playbooks');
    // Wait for the table or empty state to load
    await page.waitForLoadState('networkidle');
  });

  test('TC-080 navigate to playbooks and see the list', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Playbooks', level: 1 })).toBeVisible();
    await expect(page.getByText('Define and manage your trading strategies and setup types')).toBeVisible();
    
    // There should be at least the seeded playbooks, so table should be visible
    await expect(page.locator('table')).toBeVisible();
  });

  test('TC-081 create a new playbook, edit it, and save', async ({ page }) => {
    const playbookName = `My E2E Test Playbook ${Date.now()}`;
    // 1. Click "New Playbook"
    await page.getByRole('button', { name: 'New Playbook' }).click();
    
    // 2. Wait for navigation to the editor
    await page.waitForURL(/\/dashboard\/library\/playbooks\/[a-zA-Z0-9-]+/);
    
    // 3. Edit name
    await page.getByRole('button', { name: /Untitled Playbook/ }).click();
    await page.locator('input[value^="Untitled Playbook"]').fill(playbookName);
    await page.keyboard.press('Enter');
    
    // 4. Edit target winrate
    const targetWinrateInput = page.locator('input[type="number"]');
    await targetWinrateInput.fill('65.5');
    
    // 5. Write content in markdown
    const textarea = page.getByRole('textbox', { name: 'Playbook content (Markdown)' });
    await textarea.fill('# E2E Strategy\n\nThis is a test strategy.');
    
    // 6. Preview markdown
    await page.getByRole('button', { name: 'Preview' }).click();
    await expect(page.locator('.prose')).toContainText('E2E Strategy');
    await expect(page.locator('.prose')).toContainText('This is a test strategy.');
    
    // 7. Save & Close
    await page.getByRole('button', { name: 'Save & Close' }).click();
    await expect(page.getByText('Playbook saved')).toBeVisible({ timeout: 10_000 });
    
    // 8. Go back and check it's in the list
    await page.getByRole('button', { name: 'Back to playbooks' }).click();
    await page.waitForURL('/dashboard/library/playbooks');
    await expect(page.getByText(playbookName)).toBeVisible();
  });

  test('TC-082 delete a playbook', async ({ page }) => {
    const playbookName = `To Be Deleted Playbook ${Date.now()}`;
    // Create one specifically to delete to avoid breaking other tests
    await page.getByRole('button', { name: 'New Playbook' }).click();
    await page.waitForURL(/\/dashboard\/library\/playbooks\/[a-zA-Z0-9-]+/);
    
    // Rename
    await page.getByRole('button', { name: /Untitled Playbook/ }).click();
    await page.locator('input[value^="Untitled Playbook"]').fill(playbookName);
    await page.keyboard.press('Enter');
    await page.getByRole('button', { name: 'Save & Close' }).click();
    await expect(page.getByText('Playbook saved')).toBeVisible({ timeout: 10_000 });
    
    // In Read mode, click Delete and accept confirmation dialog
    page.once('dialog', (dialog) => dialog.accept());
    await page.getByRole('button', { name: 'Delete', exact: true }).click();
    
    // Wait for redirect back to the list and verify it's gone
    await page.waitForURL('/dashboard/library/playbooks');
    const row = page.locator('tr', { hasText: playbookName });
    await expect(row).not.toBeVisible();
  });
  
  test('TC-083 add and remove external links', async ({ page }) => {
    const playbookName = `Links Test Playbook ${Date.now()}`;
    // 1. Click "New Playbook"
    await page.getByRole('button', { name: 'New Playbook' }).click();
    await page.waitForURL(/\/dashboard\/library\/playbooks\/[a-zA-Z0-9-]+/);
    
    // 2. Edit name
    await page.getByRole('button', { name: /Untitled Playbook/ }).click();
    await page.locator('input[value^="Untitled Playbook"]').fill(playbookName);
    await page.keyboard.press('Enter');
    
    // 3. Add link
    await page.getByPlaceholder('Label (e.g. TradingView chart)').fill('My Setup Chart');
    await page.getByPlaceholder('https://…').fill('https://example.com/chart');
    await page.getByRole('button', { name: 'Add link' }).click();
    
    // 4. Verify link added
    const link = page.getByRole('link', { name: 'My Setup Chart' });
    await expect(link).toBeVisible({ timeout: 15_000 });
    await expect(link).toHaveAttribute('href', 'https://example.com/chart');
    
    // 5. Delete link
    await page.getByRole('button', { name: 'Delete link My Setup Chart' }).click();
    await expect(link).not.toBeVisible({ timeout: 20_000 });
  });
});
