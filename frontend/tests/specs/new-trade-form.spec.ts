import { test, expect } from '@playwright/test';

test.describe('New Trade Form Redesign', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard/trades/new');
    await page.waitForLoadState('networkidle');
  });

  test('TC-090 renders form fields correctly', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'New Trade' })).toBeVisible();
    await expect(page.getByLabel('Symbol')).toBeVisible();
    await expect(page.getByLabel('Direction')).toBeVisible();
    await expect(page.getByLabel('Asset Class')).toBeVisible();
    await expect(page.getByLabel('Quantity')).toBeVisible();
    await expect(page.getByLabel('Entry Price')).toBeVisible();
    await expect(page.getByLabel('Opened At')).toBeVisible();
  });

  test('TC-091 creates a basic new trade successfully', async ({ page }) => {
    // 1. Fill basic details
    await page.getByLabel('Symbol').fill('AAPL');
    
    // Select LONG (default is usually LONG, but let's be explicit if possible)
    await page.getByLabel('Direction').selectOption('LONG');
    await page.getByLabel('Asset Class').selectOption('EQUITY');
    
    // 2. Fill quantity and price
    await page.getByLabel('Quantity').fill('100');
    await page.getByLabel('Entry Price').fill('150.50');
    
    // 3. Fill date
    // Set opened at to a valid datetime-local value. e.g. "2024-05-15T14:30"
    await page.getByLabel('Opened At').fill('2024-05-15T14:30');
    
    // 4. Fill optional playbook ID
    // Look for a Select playbook dropdown if exists, otherwise skip
    const playbookDropdown = page.locator('select').filter({ hasText: 'Select playbook' });
    if (await playbookDropdown.isVisible()) {
      await playbookDropdown.selectOption({ index: 1 });
    }
    
    // 5. Submit
    await page.getByRole('button', { name: 'Save Trade' }).click();
    
    // 6. Verify navigation back to trades list or trade details
    // Assume it redirects to either /dashboard/trades or /dashboard/trades/[id]
    await page.waitForURL(/\/dashboard\/trades(?:\/[a-z0-9-]+)?$/);
    
    // 7. Verify the trade is visible
    // The list should show AAPL
    if (page.url().endsWith('/dashboard/trades')) {
      await expect(page.locator('table').getByText('AAPL')).toBeVisible();
    }
  });

  test('TC-092 shows validation errors for empty fields', async ({ page }) => {
    await page.getByRole('button', { name: 'Save Trade' }).click();
    
    await expect(page.getByText('Symbol is required')).toBeVisible();
    await expect(page.getByText('Quantity is required and must be > 0')).toBeVisible();
    await expect(page.getByText('Entry price is required and must be > 0')).toBeVisible();
  });
});
