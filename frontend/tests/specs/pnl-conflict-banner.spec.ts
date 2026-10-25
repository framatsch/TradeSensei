import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

const IBKR_FIXTURE = path.join(__dirname, '../fixtures/ibkr-sample.xml');
const SEED_STATE_FILE = path.join(__dirname, '../.auth/seed-state.json');

function getSeedState() {
  try {
    return JSON.parse(fs.readFileSync(SEED_STATE_FILE, 'utf-8'));
  } catch {
    return { accountId: '', portfolioId: '', conflictAccountId: '', manualLinkAccountId: '' };
  }
}

function buildIbkrXmlBuffer(txPrefix: string, extraTradesXml = ''): Buffer {
  const raw = fs.readFileSync(IBKR_FIXTURE, 'utf-8').replace(/E2E-T/g, txPrefix);
  if (!extraTradesXml) return Buffer.from(raw, 'utf-8');
  return Buffer.from(raw.replace('</Trades>', `${extraTradesXml}\n      </Trades>`), 'utf-8');
}

test.describe('PnL Conflict Banner & Manual Link', () => {
  test.setTimeout(60_000);
  test.use({ storageState: './frontend/tests/.auth/user.json' });

  test('TC-CONFLICT — banner renders on duplicate leg and clears when deleted', async ({ page }) => {
    const { accountId, conflictAccountId, portfolioId } = getSeedState();
    const targetAccountId = conflictAccountId || accountId;
    test.skip(!targetAccountId || !portfolioId, 'No seeded account or portfolio found');

    const xmlBuffer = buildIbkrXmlBuffer('CONFLICT-T');

    // 1. Initial import of the IBKR fixture via UI
    await page.goto('/dashboard/trades/import');
    await page.getByRole('combobox').selectOption({ value: targetAccountId });
    await page.locator('input[type="file"]').setInputFiles({
      name: 'ibkr-conflict.xml',
      mimeType: 'application/xml',
      buffer: xmlBuffer,
    });
    await page.getByRole('button', { name: /^Import \d+ file/i }).click();
    await expect(page.getByText(/Import complete/i)).toBeVisible({ timeout: 15000 });

    // 2. Add a manual execution that duplicates the MSFT entry
    // MSFT from fixture: 2026-01-11 11:15:00 UTC, Qty 5, Price 410.10, LONG
    await page.goto(`/dashboard/trades?account_id=${targetAccountId}&symbol=MSFT&opened_at_from=2026-01-01`);
    await page.getByRole('link', { name: /MSFT/ }).first().click();
    await expect(page.getByRole('heading', { name: /MSFT/ })).toBeVisible();

    const localExecutedAt = await page.evaluate(() => {
      const d = new Date('2026-01-11T11:15:00Z');
      const pad = (n: number) => String(n).padStart(2, '0');
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
    });

    // Add manual leg matching the imported MSFT entry leg
    await page.getByRole('button', { name: /Add Execution/i }).click();
    const addForm = page.locator('#add-execution-form');
    await expect(addForm).toBeVisible();
    await page.getByLabel('Executed At').fill(localExecutedAt);
    await page.getByLabel('Quantity').fill('5');
    await page.getByLabel('Price').fill('410.10');
    await addForm.getByRole('button', { name: 'Add Execution' }).click();
    await expect(addForm).not.toBeVisible({ timeout: 15000 });

    // 3. Verify conflict banner is visible
    const banner = page.getByText('Position Conflict');
    await expect(banner).toBeVisible({ timeout: 10000 });

    // 4. Delete the manual leg
    const legsTable = page.locator('#executions-table table');
    const manualRow = legsTable.locator('tbody tr').filter({ hasText: /Manual/i }).first();
    await manualRow.getByRole('button', { name: 'Row actions' }).click();
    await page.getByRole('menuitem', { name: 'Delete', exact: true }).click();
    await legsTable.getByRole('button', { name: 'Delete', exact: true }).click();

    // 5. Verify banner is gone
    await expect(banner).not.toBeVisible({ timeout: 10000 });
  });

  test('TC-MANUALLINK — can link manual execution to broker transaction', async ({ page }) => {
    const { accountId, manualLinkAccountId, portfolioId } = getSeedState();
    const targetAccountId = manualLinkAccountId || accountId;
    test.skip(!targetAccountId || !portfolioId, 'No seeded account or portfolio found');

    // Include a closing fill for NVDA so the trade is closed and visible in the default trade list
    const xmlBuffer = buildIbkrXmlBuffer(
      'MANUALLINK-T',
      '        <Trade assetCategory="STK" symbol="NVDA" tradeDate="20260115" dateTime="20260115;151500" quantity="-2" tradePrice="710.00" ibCommission="-1.00" currency="USD" transactionID="MANUALLINK-T0006" fifoPnlRealized="19.00" />'
    );

    // When deleting the imported execution, pass reset=true so its source_id link is released
    // while keeping the BrokerRawTransaction available for manual linking.
    await page.route('**/api/v1/portfolios/*/executions/*', async (route) => {
      if (route.request().method() === 'DELETE') {
        const url = new URL(route.request().url());
        url.searchParams.set('reset', 'true');
        await route.continue({ url: url.toString() });
      } else {
        await route.continue();
      }
    });

    // 1. Initial import of the IBKR fixture via UI
    await page.goto('/dashboard/trades/import');
    await page.getByRole('combobox').selectOption({ value: targetAccountId });
    await page.locator('input[type="file"]').setInputFiles({
      name: 'ibkr-manuallink.xml',
      mimeType: 'application/xml',
      buffer: xmlBuffer,
    });
    await page.getByRole('button', { name: /^Import \d+ file/i }).click();
    await expect(page.getByText(/Import complete/i)).toBeVisible({ timeout: 15000 });

    // 2. Go to NVDA trade, delete the first imported leg, then create a manual replacement leg
    await page.goto(`/dashboard/trades?account_id=${targetAccountId}&symbol=NVDA&opened_at_from=2026-01-01`);
    await page.getByRole('link', { name: /NVDA/ }).first().click();
    await expect(page.getByRole('heading', { name: /NVDA/ })).toBeVisible();

    const legsTable = page.locator('#executions-table table');
    await expect(legsTable.locator('tbody tr')).toHaveCount(2, { timeout: 15000 });

    const firstRow = legsTable.locator('tbody tr').first();
    await firstRow.getByRole('button', { name: 'Row actions' }).click();
    await page.getByRole('menuitem', { name: 'Delete', exact: true }).click();
    await legsTable.getByRole('button', { name: 'Delete', exact: true }).click();
    await expect(legsTable.locator('tbody tr')).toHaveCount(1, { timeout: 15000 });

    // Add manual leg
    await page.getByRole('button', { name: /Add Execution/i }).click();
    const addForm = page.locator('#add-execution-form');
    await expect(addForm).toBeVisible();
    await page.getByLabel('Executed At').fill('2026-01-12T12:15');
    await page.getByLabel('Quantity').fill('2');
    await page.getByLabel('Price').fill('700.50');
    await addForm.getByRole('button', { name: 'Add Execution' }).click();
    await expect(addForm).not.toBeVisible({ timeout: 15000 });

    // Wait for the manual row to appear
    const manualRow = legsTable.locator('tbody tr').filter({ hasText: /Manual/i }).first();
    await expect(manualRow).toBeVisible({ timeout: 15000 });

    // 3. Link broker transaction
    await manualRow.getByRole('button', { name: 'Row actions' }).click();
    await page.getByRole('menuitem', { name: /Link broker transaction/i }).click();

    // Dialog should open
    await expect(page.getByRole('heading', { name: /Link broker transaction/i })).toBeVisible({ timeout: 15000 });

    // Setup network listener to assert request payload
    const requestPromise = page.waitForRequest((req) =>
      req.url().includes('link-broker-transaction') && req.method() === 'POST'
    );

    // Pick the released NVDA transaction (MANUALLINK-T0003)
    await page.getByRole('button', { name: /Select broker transaction.*MANUALLINK-T0003/i }).click();

    // Confirm link
    await page.getByRole('button', { name: /Link transaction/i }).click();

    const linkRequest = await requestPromise;
    const postData = linkRequest.postDataJSON();
    expect(postData).toHaveProperty('raw_transaction_id');

    // Verify success by checking modal closes
    await expect(page.getByRole('heading', { name: /Link broker transaction/i })).not.toBeVisible();
  });
});
