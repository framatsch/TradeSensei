import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

const IBKR_FIXTURE = path.join(__dirname, '../fixtures/ibkr-sample.xml');
const SEED_STATE_FILE = path.join(__dirname, '../.auth/seed-state.json');

function getSeedState() {
  try {
    return JSON.parse(fs.readFileSync(SEED_STATE_FILE, 'utf-8'));
  } catch {
    return { accountId: '', portfolioId: '', reimportAccountId: '' };
  }
}

function buildIbkrXmlBuffer(txPrefix: string, extraTradesXml = ''): Buffer {
  const raw = fs.readFileSync(IBKR_FIXTURE, 'utf-8').replace(/E2E-T/g, txPrefix);
  if (!extraTradesXml) return Buffer.from(raw, 'utf-8');
  return Buffer.from(raw.replace('</Trades>', `${extraTradesXml}\n      </Trades>`), 'utf-8');
}

test.describe('Re-import Protection', () => {
  test.setTimeout(60_000);
  test.use({ storageState: './frontend/tests/.auth/user.json' });

  test('TC-REIMPORT — user-modified split leg and trade notes are preserved on re-import', async ({ page }) => {
    const { accountId, reimportAccountId, portfolioId } = getSeedState();
    const targetAccountId = reimportAccountId || accountId;
    test.skip(!targetAccountId || !portfolioId, 'No seeded account or portfolio found');

    const initialXmlBuffer = buildIbkrXmlBuffer('REIMPORT-T');

    // 1. Initial import of the IBKR fixture via UI
    await page.goto('/dashboard/trades/import');
    await page.getByRole('combobox').selectOption({ value: targetAccountId });
    await page.locator('input[type="file"]').setInputFiles({
      name: 'ibkr-reimport-1.xml',
      mimeType: 'application/xml',
      buffer: initialXmlBuffer,
    });
    await page.getByRole('button', { name: /^Import \d+ file/i }).click();
    await expect(page.getByText(/Import complete/i)).toBeVisible({ timeout: 15000 });

    // 2. Find the imported AAPL trade and edit its journal and execution leg
    await page.goto(`/dashboard/trades?account_id=${targetAccountId}&symbol=AAPL&opened_at_from=2026-01-01`);
    await page.getByRole('link', { name: /AAPL/ }).first().click();

    // Wait for trade detail page to load
    await expect(page.getByRole('heading', { name: /AAPL/ })).toBeVisible();

    // Edit trade journal in Qualitative Analysis & Metadata panel
    const noteText = `Test notes for re-import protection ${Date.now()}`;
    await page.getByRole('button', { name: 'Edit journal' }).click();
    await page
      .getByPlaceholder(/Write your post-trade summary/i)
      .fill(noteText);
    await page.getByRole('button', { name: 'Done Editing' }).click();
    await page.getByRole('button', { name: 'Save', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Save', exact: true })).not.toBeVisible();
    await expect(page.getByText(noteText)).toBeVisible();

    // Edit an execution leg (make it user_modified)
    const legsTable = page.locator('#executions-table table');
    const firstRow = legsTable.locator('tbody tr').first();
    await firstRow.getByRole('button', { name: 'Row actions' }).click();
    await page.getByRole('menuitem', { name: 'Edit', exact: true }).click();

    // Modify quantity slightly
    const qtyInput = firstRow.getByLabel('Quantity');
    await qtyInput.fill('15');
    await firstRow.getByTitle('Save').click();

    // Ensure save completes
    await expect(firstRow).toContainText('15', { timeout: 15000 });

    // 3. Re-import with an additional fill so the projection rebuild runs on targetAccountId
    const reimportXmlBuffer = buildIbkrXmlBuffer(
      'REIMPORT-T',
      '        <Trade assetCategory="STK" symbol="NVDA" tradeDate="20260115" dateTime="20260115;151500" quantity="-2" tradePrice="710.00" ibCommission="-1.00" currency="USD" transactionID="REIMPORT-T0006" fifoPnlRealized="19.00" />'
    );
    await page.goto('/dashboard/trades/import');
    await page.getByRole('combobox').selectOption({ value: targetAccountId });
    await page.locator('input[type="file"]').setInputFiles({
      name: 'ibkr-reimport-2.xml',
      mimeType: 'application/xml',
      buffer: reimportXmlBuffer,
    });

    // By default, overwrite user modifications is false
    const uploadBtn = page.getByRole('button', { name: /^Import \d+ file/i });
    await uploadBtn.click();
    await expect(page.getByText(/Import complete/i)).toBeVisible({ timeout: 15000 });

    // 4. Verify modifications are preserved
    await page.goto(`/dashboard/trades?account_id=${targetAccountId}&symbol=AAPL&opened_at_from=2026-01-01`);
    await page.getByRole('link', { name: /AAPL/ }).first().click();

    await expect(page.getByRole('heading', { name: /AAPL/ })).toBeVisible();

    // Trade journal notes should still be there
    await expect(page.getByText(noteText)).toBeVisible({ timeout: 15000 });

    // Execution leg should still have the modified quantity 15
    const verifyTable = page.locator('#executions-table table');
    await expect(verifyTable.locator('tbody tr').first()).toContainText('15', { timeout: 15000 });
  });
});
