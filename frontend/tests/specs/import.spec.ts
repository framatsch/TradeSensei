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
 * Import Spec — covers the broker file import page.
 *
 * The import page uses an account-first flow:
 *  Step 1 — Select an account
 *  Step 2 — Choose import method (file upload or API sync)
 *
 * global-setup seeds IBKR and Schwab accounts; IDs are read from .auth/seed-state.json.
 *
 * Tests:
 *  - Page renders heading and step 1 account selector
 *  - Account selector shows the seeded account
 *  - After selecting account, Step 2 becomes visible
 *  - File upload section is reachable
 *  - Upload button disabled without files; enabled after file selection
 *  - Successful IBKR import shows per-file result in the queue
 *  - Successful Schwab import on a Schwab account
 *
 * All tests run as the seeded E2E user.
 */

import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

const IBKR_FIXTURE = path.join(
  __dirname,
  '../fixtures/ibkr-sample.xml'
);
const SCHWAB_FIXTURE = path.join(
  __dirname,
  '../fixtures/schwab-sample.json'
);
const SEED_STATE_FILE = path.join(__dirname, '../.auth/seed-state.json');
const IMPORT_RESULT_TIMEOUT_MS = 30_000;

function getSeedState(): { accountId: string; schwabAccountId: string } {
  try {
    return JSON.parse(fs.readFileSync(SEED_STATE_FILE, 'utf-8')) as {
      accountId: string;
      schwabAccountId: string;
    };
  } catch {
    return { accountId: '', schwabAccountId: '' };
  }
}

async function expectImportQueueFinished(page: import('@playwright/test').Page): Promise<void> {
  // In full-suite runs imports can take noticeably longer than isolated runs.
  // Wait for the queue summary state instead of short-lived per-row text.
  await expect(page.getByText(/Import complete — \d+ file/i)).toBeVisible({
    timeout: IMPORT_RESULT_TIMEOUT_MS,
  });
}

test.describe('Import Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard/trades/import');
    await page.waitForLoadState('networkidle');
  });

  test('TC-070 renders page heading and subtitle', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Import Trades' })).toBeVisible();
    await expect(page.getByText('Upload a broker activity file')).toBeVisible();
  });

  test('TC-071 Step 1 account selector is visible', async ({ page }) => {
    await expect(page.getByText('Step 1 — Select Account')).toBeVisible();
    // A select dropdown should be present for account selection
    await expect(page.getByRole('combobox')).toBeVisible();
  });

  test('TC-072 account selector includes the seeded E2E account', async ({ page }) => {
    const { accountId } = getSeedState();
    test.skip(!accountId, 'No seeded account ID found — skipping');

    const select = page.getByRole('combobox');
    await expect(select).toBeVisible();

    // Wait for options to be populated — accounts are fetched asynchronously
    const accountOption = page.locator('select option').filter({ hasText: 'E2E Test Account' }).first();
    await expect(accountOption).toBeAttached({ timeout: 10_000 });
    const optionText = await accountOption.textContent();
    expect(optionText).toContain('E2E Test Account');
  });

  test('TC-073 selecting an account shows Step 2', async ({ page }) => {
    const { accountId } = getSeedState();
    test.skip(!accountId, 'No seeded account ID found — skipping');

    // Select the seeded account
    await page.getByRole('combobox').selectOption({ value: accountId });

    // Step 2 should now appear
    await expect(page.getByText('Step 2 — Import Trades')).toBeVisible({ timeout: 5_000 });
  });

  test('TC-074 file upload section accessible after account selection', async ({ page }) => {
    const { accountId } = getSeedState();
    test.skip(!accountId, 'No seeded account ID found — skipping');

    await page.getByRole('combobox').selectOption({ value: accountId });
    await expect(page.getByText('Step 2 — Import Trades')).toBeVisible({ timeout: 5_000 });

    // The "Upload Files" option should be present (either a button or a section heading)
    // API Sync section may be present but no API credentials — file upload section is visible
    await expect(page.getByText(/Upload Files|Upload a file|File Upload/i)).toBeVisible({
      timeout: 5_000,
    });
  });

  test('TC-075 Upload button absent (not rendered) before a file is selected', async ({ page }) => {
    const { accountId } = getSeedState();
    test.skip(!accountId, 'No seeded account ID found — skipping');

    await page.getByRole('combobox').selectOption({ value: accountId });
    await expect(page.getByText('Step 2 — Import Trades')).toBeVisible({ timeout: 5_000 });

    // For API accounts (ibkr/schwab) the file section is collapsed by default.
    // Expand it so we can verify the upload button is absent before file selection.
    const toggleBtn = page.getByRole('button', { name: /Or upload files manually/i });
    await expect(toggleBtn).toBeVisible({ timeout: 5_000 });
    await toggleBtn.click();

    // After expanding, the file input is visible but no "Import N files" button yet
    await expect(page.locator('input[type="file"]')).toBeVisible({ timeout: 5_000 });
    // The start-upload button should NOT be present (it only appears after file selection)
    await expect(page.getByRole('button', { name: /^Import \d+ file/i })).toHaveCount(0);
  });

  test('TC-076 successful IBKR import shows result per file', async ({ page }) => {
    const { accountId } = getSeedState();
    test.skip(!accountId, 'No seeded account ID found — skipping');

    await page.getByRole('combobox').selectOption({ value: accountId });
    await expect(page.getByText('Step 2 — Import Trades')).toBeVisible({ timeout: 5_000 });

    // For API accounts the file section is collapsed by default — expand it first.
    // Wait for the toggle button to be visible, then click it.
    const toggleBtn = page.getByRole('button', { name: /Or upload files manually/i });
    await expect(toggleBtn).toBeVisible({ timeout: 5_000 });
    await toggleBtn.click();

    // File input should now be visible
    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toBeVisible({ timeout: 5_000 });
    await fileInput.setInputFiles(IBKR_FIXTURE);

    // After file selection, the "Import N file(s)" start button appears
    const uploadBtn = page.getByRole('button', { name: /^Import \d+ file/i });
    await expect(uploadBtn).toBeVisible({ timeout: 5_000 });
    await expect(uploadBtn).toBeEnabled();
    await uploadBtn.click();

    // Wait for result to appear: "created", "skipped", "Import complete", or an error message
    await expectImportQueueFinished(page);
  });

  test('TC-077 successful Schwab import shows result per file', async ({ page }) => {
    const { schwabAccountId } = getSeedState();
    test.skip(!schwabAccountId, 'No seeded Schwab account ID found — skipping');

    await page.getByRole('combobox').selectOption({ value: schwabAccountId });
    await expect(page.getByText('Step 2 — Import Trades')).toBeVisible({ timeout: 5_000 });

    const toggleBtn = page.getByRole('button', { name: /Or upload files manually/i });
    await expect(toggleBtn).toBeVisible({ timeout: 5_000 });
    await toggleBtn.click();

    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toBeVisible({ timeout: 5_000 });
    await fileInput.setInputFiles(SCHWAB_FIXTURE);

    const uploadBtn = page.getByRole('button', { name: /^Import \d+ file/i });
    await expect(uploadBtn).toBeVisible({ timeout: 5_000 });
    await expect(uploadBtn).toBeEnabled();
    await uploadBtn.click();

    await expectImportQueueFinished(page);
  });
});
