import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

const IBKR_FIXTURE = path.join(__dirname, '../fixtures/ibkr-sample.xml');
const SEED_STATE_FILE = path.join(__dirname, '../.auth/seed-state.json');

function getSeedState() {
  try {
    return JSON.parse(fs.readFileSync(SEED_STATE_FILE, 'utf-8'));
  } catch {
    return { accountId: '', portfolioId: '' };
  }
}

test.describe('Re-import Protection', () => {
  test.use({ storageState: './frontend/tests/.auth/user.json' });

  test('TC-REIMPORT — user-modified split leg and trade notes are preserved on re-import', async ({ page, request }) => {
    const { accountId, portfolioId } = getSeedState();
    test.skip(!accountId || !portfolioId, 'No seeded account or portfolio found');

    // 1. Initial import of the IBKR fixture via API
    const formData = new FormData();
    formData.append('broker', 'ibkr');
    formData.append('account_id', accountId);
    
    // We have to build multipart data manually or use fetch since Playwright APIRequestContext doesn't support FormData directly
    // Instead of using API to upload, we can just use the UI to upload it first.
    await page.goto('/dashboard/trades/import');
    await page.getByRole('combobox').selectOption({ value: accountId });
    await page.locator('input[type="file"]').setInputFiles(IBKR_FIXTURE);
    await page.getByRole('button', { name: /^Import \d+ file/i }).click();
    await expect(page.getByText(/Import complete/i)).toBeVisible({ timeout: 15000 });

    // 2. Find the AAPL trade and edit it
    await page.goto('/dashboard/trades');
    await page.getByRole('link', { name: /AAPL/ }).first().click();
    
    // Wait for trade detail page to load
    await expect(page.getByRole('heading', { name: /AAPL/ })).toBeVisible();
    
    // Edit trade notes
    await page.getByRole('button', { name: /Edit notes/i }).click();
    await page.locator('textarea[name="notes"]').fill('Test notes for re-import protection');
    await page.getByRole('button', { name: /Save/i }).click();
    await expect(page.getByText('Test notes for re-import protection')).toBeVisible();

    // Edit an execution leg (make it user_modified)
    const legsTable = page.locator('table').filter({ hasText: 'Executions' });
    const firstRow = legsTable.locator('tbody tr').first();
    await firstRow.getByRole('button', { name: 'Row actions' }).click(); // Open actions menu
    await page.getByRole('button', { name: 'Edit', exact: true }).click();
    
    // Modify quantity slightly
    const qtyInput = firstRow.getByLabel('Quantity');
    await qtyInput.fill('15');
    await firstRow.getByTitle('Save').click();
    
    // Ensure save completes
    await expect(firstRow).toContainText('15');
    
    // 3. Re-import the same file via UI
    await page.goto('/dashboard/trades/import');
    await page.getByRole('combobox').selectOption({ value: accountId });
    await page.locator('input[type="file"]').setInputFiles(IBKR_FIXTURE);
    
    // By default, overwrite user modifications is false
    const uploadBtn = page.getByRole('button', { name: /^Import \d+ file/i });
    await uploadBtn.click();
    await expect(page.getByText(/Import complete/i)).toBeVisible({ timeout: 15000 });

    // 4. Verify modifications are preserved
    await page.goto('/dashboard/trades');
    await page.getByRole('link', { name: /AAPL/ }).first().click();
    
    await expect(page.getByRole('heading', { name: /AAPL/ })).toBeVisible();
    
    // Trade notes should still be there
    await expect(page.getByText('Test notes for re-import protection')).toBeVisible();
    
    // Execution leg should still have the modified quantity 15
    const verifyTable = page.locator('table').filter({ hasText: 'Executions' });
    await expect(verifyTable.locator('tbody tr').first()).toContainText('15');
  });
});
