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
 * Accounts Spec — covers IBKR account creation, editing, and deletion.
 *
 * Accounts are managed under /dashboard/settings?tab=integrations
 * on the "Accounts & Integrations" tab.
 *
 * TC-080  Accounts tab renders with "New Account" button
 * TC-081  Create a manual account
 * TC-082  Create an IBKR account with credentials (full happy path)
 * TC-083  IBKR credential fields appear when type is changed to IBKR
 * TC-084  Create a Schwab account
 * TC-085  Edit an existing account name
 * TC-086  Delete an account
 *
 * All tests run as the seeded E2E user (storageState from global-setup.ts).
 */

import { test, expect, type Page } from '@playwright/test';

const SETTINGS_ACCOUNTS_URL = '/dashboard/settings?tab=integrations';

// Navigate to the Accounts & Integrations tab and wait for it to be ready
async function gotoAccountsTab(page: Page) {
  await page.goto(SETTINGS_ACCOUNTS_URL);
  await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible({ timeout: 10_000 });
  // Ensure the integrations tab is active (URL param drives it via useEffect)
  await expect(page.getByRole('heading', { name: 'Portfolios & Brokers' })).toBeVisible({ timeout: 8_000 });
}

// Expand the first portfolio if not already expanded
async function expandFirstPortfolio(page: Page) {
  const addBtn = page.getByRole('button', { name: /Add Broker Account/i }).first();
  try {
    await addBtn.waitFor({ state: 'attached', timeout: 2000 });
  } catch (e) {
    const chevronBtn = page.locator('.bg-card button', { hasText: 'USD' }).first();
    if (await chevronBtn.isVisible()) {
      await chevronBtn.click();
      await addBtn.waitFor({ state: 'attached', timeout: 3000 });
    }
  }
}

// Open the "New Account" inline form
async function openNewAccountForm(page: Page) {
  await expandFirstPortfolio(page);
  
  const addBtn = page.getByRole('button', { name: /Add Broker Account/i }).first();
  if (!(await addBtn.isVisible())) {
     const portfolioBtn = page.locator('button').filter({ hasText: /Portfolio/i }).first();
     if (await portfolioBtn.isVisible()) await portfolioBtn.click();
  }
  
  await addBtn.click();
  await expect(page.getByRole('heading', { name: 'Connect Broker Account' })).toBeVisible({ timeout: 5_000 });
}

test.describe('Accounts', () => {
  // Accept window.confirm dialogs (used by the Delete confirmation)
  test.beforeEach(async ({ page }) => {
    page.on('dialog', async (dialog) => {
      console.log(`Dialog message: ${dialog.message()}`);
      await dialog.accept();
    });
    await gotoAccountsTab(page);
    // TC-081 needs a long timeout for deletion to propagate to the UI
    test.setTimeout(45_000);
  });

  // ─── TC-080: Tab renders ────────────────────────────────────────────────────

  test('TC-080 accounts tab renders with new-account button', async ({ page }) => {
    // If there's multiple portfolios, we might need to expand one to see the Add Broker Account button
    await expandFirstPortfolio(page);
    await expect(page.getByRole('button', { name: /Add Broker Account/i }).first()).toBeAttached();

    // Tab bar has "Portfolios & Brokers" as active tab
    await expect(
      page.getByRole('button', { name: 'Portfolios & Brokers' })
    ).toBeVisible();
  });

  // ─── TC-081: Create manual account ─────────────────────────────────────────

  test('TC-081 create a manual account', async ({ page }) => {
    await openNewAccountForm(page);

    await page.getByLabel('Name').fill('My Manual Account TC081');
    await page.getByLabel('Broker Type').selectOption('manual');

    await page.getByRole('button', { name: 'Connect Account' }).click();

    await expect(page.getByText('My Manual Account TC081')).toBeVisible({
      timeout: 8_000,
    });

    // Clean up
    const rowBtn = page.getByText('My Manual Account TC081', { exact: true }).locator('..').locator('..').getByRole('button');
    await rowBtn.click(); // Click Edit button
    
    await expect(page.getByRole('heading', { name: 'Edit Account' })).toBeVisible();
    await page.getByRole('button', { name: 'Deactivate Account' }).click();
    await page.reload();
    await expect(page.getByText('My Manual Account TC081')).toHaveCount(0, {
      timeout: 15_000,
    });
  });

  // ─── TC-082: Create IBKR account (full happy path) ─────────────────────────

  test('TC-082 create an IBKR account with credentials', async ({ page }) => {
    await openNewAccountForm(page);

    // Fill base fields
    await page.getByLabel('Name').fill('IBKR Main TC082');

    // Switch type to IBKR
    await page.getByLabel('Broker Type').selectOption('ibkr');

    // IBKR credential fields appear
    await expect(page.getByLabel('Flex Token')).toBeVisible({ timeout: 3_000 });
    await expect(page.getByLabel('Flex Query ID')).toBeVisible();

    // Fill credentials
    await page.getByLabel('Flex Token').fill('test-flex-token-abc123');
    await page.getByLabel('Flex Query ID').fill('123456');

    await page.getByRole('button', { name: 'Connect Account' }).click();

    // Account row should appear
    await expect(page.getByText('IBKR Main TC082')).toBeVisible({
      timeout: 8_000,
    });

    // Clean up
    const rowBtn = page.getByText('IBKR Main TC082', { exact: true }).locator('..').locator('..').getByRole('button');
    await rowBtn.click();
    await expect(page.getByRole('heading', { name: 'Edit Account' })).toBeVisible();
    await page.getByRole('button', { name: 'Deactivate Account' }).click();
    await page.reload();
    await expect(page.getByText('IBKR Main TC082')).toHaveCount(0, {
      timeout: 15_000,
    });
  });

  // ─── TC-083: Credential fields toggle on type change ───────────────────────

  test('TC-083 credential fields appear and disappear when type changes', async ({ page }) => {
    await openNewAccountForm(page);

    // IBKR is default, so fields should be visible
    await expect(page.getByLabel('Flex Token')).toBeVisible();

    // Switch to Manual -> fields should disappear
    await page.getByLabel('Broker Type').selectOption('manual');
    await expect(page.getByLabel('Flex Token')).not.toBeVisible();
    await expect(page.getByLabel('App Key')).not.toBeVisible();

    // Switch to Schwab -> Schwab fields should appear
    await page.getByLabel('Broker Type').selectOption('schwab');
    await expect(page.getByLabel('App Key')).toBeVisible();
    await expect(page.getByLabel('App Secret')).toBeVisible();
    await expect(page.getByLabel('Flex Token')).not.toBeVisible(); // IBKR fields hidden
  });

  // ─── TC-084: Create Schwab account ─────────────────────────────────────────

  test('TC-084 create a Schwab account', async ({ page }) => {
    await openNewAccountForm(page);

    await page.getByLabel('Name').fill('Schwab TC084');
    await page.getByLabel('Broker Type').selectOption('schwab');

    await page.getByLabel('App Key').fill('test-app-key');
    await page.getByLabel('App Secret').fill('test-app-secret');

    await page.getByRole('button', { name: 'Connect Account' }).click();

    await expect(page.getByText('Schwab TC084')).toBeVisible({
      timeout: 8_000,
    });

    // Clean up
    const rowBtn = page.getByText('Schwab TC084', { exact: true }).locator('..').locator('..').getByRole('button');
    await rowBtn.click();
    await expect(page.getByRole('heading', { name: 'Edit Account' })).toBeVisible();
    await page.getByRole('button', { name: 'Deactivate Account' }).click();
    await page.reload();
    await expect(page.getByText('Schwab TC084')).toHaveCount(0, {
      timeout: 15_000,
    });
  });

  // ─── TC-085: Edit an account name ──────────────────────────────────────────

  test('TC-085 edit an existing account name', async ({ page }) => {
    await expandFirstPortfolio(page);

    // Rely on the globally seeded "E2E Test Account"
    const rowBtn = page.getByText('E2E Test Account', { exact: true }).locator('..').locator('..').getByRole('button');

    // Open Edit modal
    await rowBtn.click();
    await expect(page.getByRole('heading', { name: 'Edit Account' })).toBeVisible();

    await page.getByLabel('Name').fill('E2E Test Account - Edited');
    await page.getByRole('button', { name: 'Save Changes' }).click();

    // Verify update
    await expect(page.getByText('E2E Test Account - Edited')).toBeVisible({
      timeout: 8_000,
    });

    // Revert back so we don't break other tests
    const editBtn = page.getByText('E2E Test Account - Edited', { exact: true }).locator('..').locator('..').getByRole('button');
    await editBtn.click();
    await expect(page.getByRole('heading', { name: 'Edit Account' })).toBeVisible();
    await page.getByLabel('Name').fill('E2E Test Account');
    await page.getByRole('button', { name: 'Save Changes' }).click();

    await expect(page.getByText('E2E Test Account', { exact: true }).first()).toBeVisible({
      timeout: 8_000,
    });
  });

  // ─── TC-086: Delete an account ─────────────────────────────────────────────

  test('TC-086 delete an account removes it from the list', async ({ page }) => {
    // 1. Create a throwaway account first
    await openNewAccountForm(page);
    await page.getByLabel('Name').fill('DeleteMe TC086');
    await page.getByLabel('Broker Type').selectOption('manual');
    await page.getByRole('button', { name: 'Connect Account' }).click();

    await expect(page.getByText('DeleteMe TC086')).toBeVisible({ timeout: 8_000 });

    // 2. Delete it
    const rowBtn = page.getByText('DeleteMe TC086', { exact: true }).locator('..').locator('..').getByRole('button');
    await rowBtn.click(); // Open edit modal
    
    await expect(page.getByRole('heading', { name: 'Edit Account' })).toBeVisible();
    await page.getByRole('button', { name: 'Deactivate Account' }).click();

    await page.reload();

    // 3. Assert it's gone
    await expect(page.getByText('DeleteMe TC086')).toHaveCount(0, { timeout: 15_000 });
  });
});

