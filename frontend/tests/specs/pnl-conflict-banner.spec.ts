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

test.describe('PnL Conflict Banner & Manual Link', () => {
  test.use({ storageState: './frontend/tests/.auth/user.json' });

  test('TC-CONFLICT — banner renders on duplicate leg and clears when deleted', async ({ page, request }) => {
    const { accountId, portfolioId } = getSeedState();
    test.skip(!accountId || !portfolioId, 'No seeded account or portfolio found');

    // 1. Initial import of the IBKR fixture via UI
    await page.goto('/dashboard/trades/import');
    await page.getByRole('combobox').selectOption({ value: accountId });
    await page.locator('input[type="file"]').setInputFiles(IBKR_FIXTURE);
    await page.getByRole('button', { name: /^Import \d+ file/i }).click();
    await expect(page.getByText(/Import complete/i)).toBeVisible({ timeout: 15000 });

    // 2. Add a manual execution that duplicates the MSFT entry
    // MSFT from fixture: 2026-01-11 11:15:00, Qty 5, Price 410.10, LONG
    await page.goto('/dashboard/trades');
    await page.getByRole('link', { name: /MSFT/ }).first().click();
    await expect(page.getByRole('heading', { name: /MSFT/ })).toBeVisible();
    
    // Add manual leg
    await page.getByRole('button', { name: /Add execution/i }).click();
    await page.getByLabel('Executed at date and time').fill('2026-01-11T11:15:00');
    // Ensure direction is LONG (it defaults to LONG usually, but we can verify)
    await page.getByLabel('Quantity').fill('5');
    await page.getByLabel('Price').fill('410.10');
    await page.getByRole('button', { name: /Save/i }).click();

    // Re-import to trigger conflict detection (since conflict detection happens during aggregation post-import)
    await page.goto('/dashboard/trades/import');
    await page.getByRole('combobox').selectOption({ value: accountId });
    await page.locator('input[type="file"]').setInputFiles(IBKR_FIXTURE);
    await page.getByRole('button', { name: /^Import \d+ file/i }).click();
    await expect(page.getByText(/Import complete/i)).toBeVisible({ timeout: 15000 });

    // 3. Verify banner is visible
    await page.goto('/dashboard/trades');
    await page.getByRole('link', { name: /MSFT/ }).first().click();
    await expect(page.getByRole('heading', { name: /MSFT/ })).toBeVisible();

    const banner = page.getByText(/conflict/i);
    await expect(banner).toBeVisible();
    
    // 4. Delete the manual leg
    const legsTable = page.locator('table').filter({ hasText: 'Executions' });
    // Find the row with manual origin (can be identified if there is an indicator or just delete the second one)
    // We will just delete the first row, which will clear the conflict as long as one of the pair is deleted
    const firstRow = legsTable.locator('tbody tr').first();
    await firstRow.locator('button').last().click(); // Open actions menu
    await page.getByRole('button', { name: 'Delete', exact: true }).click();
    await page.getByRole('button', { name: 'Confirm' }).click();

    // 5. Verify banner is gone
    await expect(banner).not.toBeVisible();
  });

  test('TC-MANUALLINK — can link manual execution to broker transaction', async ({ page, request }) => {
    const { accountId, portfolioId } = getSeedState();
    test.skip(!accountId || !portfolioId, 'No seeded account or portfolio found');

    // 1. Initial import of the IBKR fixture via UI
    await page.goto('/dashboard/trades/import');
    await page.getByRole('combobox').selectOption({ value: accountId });
    await page.locator('input[type="file"]').setInputFiles(IBKR_FIXTURE);
    await page.getByRole('button', { name: /^Import \d+ file/i }).click();
    await expect(page.getByText(/Import complete/i)).toBeVisible({ timeout: 15000 });

    // 2. Go to NVDA trade, delete the imported leg, then create a manual one
    await page.goto('/dashboard/trades');
    await page.getByRole('link', { name: /NVDA/ }).first().click();
    await expect(page.getByRole('heading', { name: /NVDA/ })).toBeVisible();

    // Delete the only leg (which is imported)
    const legsTable = page.locator('table').filter({ hasText: 'Executions' });
    const firstRow = legsTable.locator('tbody tr').first();
    await firstRow.locator('button').last().click();
    await page.getByRole('button', { name: 'Delete', exact: true }).click();
    await page.getByRole('button', { name: 'Confirm' }).click();

    // Add manual leg
    await page.getByRole('button', { name: /Add execution/i }).click();
    await page.getByLabel('Executed at date and time').fill('2026-01-12T12:15:00');
    await page.getByLabel('Quantity').fill('2');
    await page.getByLabel('Price').fill('700.50');
    await page.getByRole('button', { name: /Save/i }).click();

    // Wait for the row to appear
    await expect(legsTable.locator('tbody tr')).toHaveCount(1);
    
    // 3. Link broker transaction
    const manualRow = legsTable.locator('tbody tr').first();
    await manualRow.locator('button').last().click();
    
    // Click "Link broker transaction" menu item
    await page.getByRole('button', { name: /Link broker transaction/i }).click();

    // Dialog should open
    await expect(page.getByRole('heading', { name: /Link Broker Transaction/i })).toBeVisible();

    // Setup network listener to assert request payload
    const requestPromise = page.waitForRequest(request => 
      request.url().includes('link-broker-transaction') && request.method() === 'POST'
    );

    // Pick the NVDA transaction
    // Assuming there's a list or select, let's just click the first transaction in the list
    await page.getByRole('button', { name: /Select/i }).first().click();
    
    // Confirm link
    await page.getByRole('button', { name: /Link/i, exact: true }).click();

    const linkRequest = await requestPromise;
    const postData = linkRequest.postDataJSON();
    expect(postData).toHaveProperty('raw_transaction_id');

    // Verify success toast
    await expect(page.getByText(/Successfully linked/i)).toBeVisible();
  });
});
