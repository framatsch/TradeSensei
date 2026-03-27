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
  await expect(page.getByRole('button', { name: '+ New Account' })).toBeVisible({ timeout: 8_000 });
}

// Open the "New Account" inline form
async function openNewAccountForm(page: Page) {
  await page.getByRole('button', { name: '+ New Account' }).click();
  await expect(page.getByRole('heading', { name: 'New Account' })).toBeVisible({ timeout: 5_000 });
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
    await expect(page.getByRole('button', { name: '+ New Account' })).toBeVisible();
    // Tab bar has "Accounts & Integrations" as active tab
    await expect(
      page.getByRole('button', { name: 'Accounts & Integrations' })
    ).toBeVisible();
  });

  // ─── TC-081: Create manual account ─────────────────────────────────────────

  test('TC-081 create a manual account', async ({ page }) => {
    await openNewAccountForm(page);

    await page.getByLabel('Name').fill('My Manual Account TC081');
    // type defaults to "manual" — no change needed

    await page.getByRole('button', { name: 'Create Account' }).click();

    await expect(page.getByRole('cell', { name: 'My Manual Account TC081' })).toBeVisible({
      timeout: 8_000,
    });

    // Clean up
    const row = page.getByRole('row', { name: /My Manual Account TC081/ });
    await row.getByRole('button', { name: 'Delete' }).click();
    await page.reload();
    await expect(page.getByRole('row', { name: /My Manual Account TC081/ })).toHaveCount(0, {
      timeout: 15_000,
    });
  });

  // ─── TC-082: Create IBKR account (full happy path) ─────────────────────────

  test('TC-082 create an IBKR account with credentials', async ({ page }) => {
    await openNewAccountForm(page);

    // Fill base fields
    await page.getByLabel('Name').fill('IBKR Main TC082');
    await page.getByLabel('Account Number').fill('U9998887');

    // Switch type to IBKR
    await page.getByLabel('Account Type').selectOption('ibkr');

    // IBKR credential fields appear
    await expect(page.getByLabel('Flex Token')).toBeVisible({ timeout: 3_000 });
    await expect(page.getByLabel('Flex Query ID')).toBeVisible();

    // Fill credentials
    await page.getByLabel('Flex Token').fill('test-flex-token-abc123');
    await page.getByLabel('Flex Query ID').fill('123456');

    await page.getByRole('button', { name: 'Create Account' }).click();

    // Account row should appear
    await expect(page.getByRole('cell', { name: 'IBKR Main TC082' })).toBeVisible({
      timeout: 8_000,
    });

    // IBKR type badge should be shown (the <span> inside the Type cell)
    await expect(
      page.getByRole('row', { name: /IBKR Main TC082/ }).getByText('IBKR', { exact: true }).last()
    ).toBeVisible();

    // API credentials indicator (🔑) should be visible
    await expect(page.getByTitle('API credentials stored')).toBeVisible();

    // No server error
    await expect(page.locator('text=Internal Server Error')).not.toBeVisible();
    await expect(page.locator('text=500')).not.toBeVisible();

    // Clean up
    const row = page.getByRole('row', { name: /IBKR Main TC082/ });
    await row.getByRole('button', { name: 'Delete' }).click();
    await page.reload();
    await expect(page.getByRole('row', { name: /IBKR Main TC082/ })).toHaveCount(0);
  });

  // ─── TC-083: Credential fields toggle on type change ───────────────────────

  test('TC-083 credential fields appear and disappear when type changes', async ({ page }) => {
    await openNewAccountForm(page);

    // Manual — no credential fields
    await expect(page.getByLabel('Flex Token')).not.toBeVisible();
    await expect(page.getByLabel('App Key')).not.toBeVisible();

    // Switch to Schwab
    await page.getByLabel('Account Type').selectOption('schwab');
    await expect(page.getByLabel('App Key')).toBeVisible({ timeout: 3_000 });
    await expect(page.getByLabel('App Secret')).toBeVisible();
    await expect(page.getByLabel('Flex Token')).not.toBeVisible();

    // Switch to IBKR
    await page.getByLabel('Account Type').selectOption('ibkr');
    await expect(page.getByLabel('Flex Token')).toBeVisible({ timeout: 3_000 });
    await expect(page.getByLabel('Flex Query ID')).toBeVisible();
    await expect(page.getByLabel('App Key')).not.toBeVisible();

    // Switch back to Manual
    await page.getByLabel('Account Type').selectOption('manual');
    await expect(page.getByLabel('Flex Token')).not.toBeVisible();
    await expect(page.getByLabel('App Key')).not.toBeVisible();

    await page.getByRole('button', { name: 'Cancel' }).click();
    await expect(page.getByRole('heading', { name: 'New Account' })).not.toBeVisible();
  });

  // ─── TC-084: Create Schwab account ─────────────────────────────────────────

  test('TC-084 create a Schwab account', async ({ page }) => {
    await openNewAccountForm(page);

    await page.getByLabel('Name').fill('Schwab Cash TC084');
    await page.getByLabel('Account Type').selectOption('schwab');

    await expect(page.getByLabel('App Key')).toBeVisible({ timeout: 3_000 });
    await page.getByLabel('App Key').fill('schwab-app-key-test');
    await page.getByLabel('App Secret').fill('schwab-app-secret-test');

    await page.getByRole('button', { name: 'Create Account' }).click();

    await expect(page.getByRole('cell', { name: 'Schwab Cash TC084' })).toBeVisible({
      timeout: 8_000,
    });
    await expect(
      page.getByRole('row', { name: /Schwab Cash TC084/ }).getByText('Schwab', { exact: true }).last()
    ).toBeVisible();

    // Clean up
    const row = page.getByRole('row', { name: /Schwab Cash TC084/ });
    await row.getByRole('button', { name: 'Delete' }).click();
    await page.reload();
    await expect(page.getByRole('row', { name: /Schwab Cash TC084/ })).toHaveCount(0);
  });

  // ─── TC-085: Edit an account name ──────────────────────────────────────────

  test('TC-085 edit an existing account name', async ({ page }) => {
    // Create an account to edit
    await openNewAccountForm(page);
    await page.getByLabel('Name').fill('Account To Edit TC085');
    await page.getByRole('button', { name: 'Create Account' }).click();
    await expect(page.getByRole('cell', { name: 'Account To Edit TC085' })).toBeVisible({
      timeout: 8_000,
    });

    // Click Edit
    const row = page.getByRole('row', { name: /Account To Edit TC085/ });
    await row.getByRole('button', { name: 'Edit' }).click();

    await expect(page.getByRole('heading', { name: 'Edit Account' })).toBeVisible({
      timeout: 5_000,
    });

    // Update the name
    const nameInput = page.getByLabel('Name');
    await nameInput.clear();
    await nameInput.fill('Account Renamed TC085');

    await page.getByRole('button', { name: 'Save Changes' }).click();

    // Updated row visible, old name gone
    await expect(page.getByRole('cell', { name: 'Account Renamed TC085' })).toBeVisible({
      timeout: 8_000,
    });
    await expect(page.getByRole('cell', { name: 'Account To Edit TC085' })).not.toBeVisible();

    // Clean up
    const updatedRow = page.getByRole('row', { name: /Account Renamed TC085/ });
    await updatedRow.getByRole('button', { name: 'Delete' }).click();
    await page.reload();
    await expect(page.getByRole('row', { name: /Account Renamed TC085/ })).toHaveCount(0, {
      timeout: 10_000,
    });
  });

  // ─── TC-086: Delete an account ─────────────────────────────────────────────

  test('TC-086 delete an account removes it from the list', async ({ page }) => {
    // Create throwaway account
    await openNewAccountForm(page);
    await page.getByLabel('Name').fill('Account To Delete TC086');
    await page.getByRole('button', { name: 'Create Account' }).click();
    await expect(page.getByRole('cell', { name: 'Account To Delete TC086' })).toBeVisible({
      timeout: 8_000,
    });

    // Delete
    const row = page.getByRole('row', { name: /Account To Delete TC086/ });
    await row.getByRole('button', { name: 'Delete' }).click();
    await page.reload();
    await expect(page.getByRole('row', { name: /Account To Delete TC086/ })).toHaveCount(0);
  });
});
