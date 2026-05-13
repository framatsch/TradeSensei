import { test, expect } from '@playwright/test';

test.describe('Metrics (Annotations) Library', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard/library/metrics');
    await page.waitForLoadState('networkidle');
  });

  test('TC-110 navigate to metrics page and see the list', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Metrics' })).toBeVisible();
    await expect(page.getByText('Manage reusable annotation definitions')).toBeVisible();
    
    // The table should be visible
    await expect(page.locator('table')).toBeVisible();
  });

  test('TC-111 create a new metric (int)', async ({ page }) => {
    // 1. Click "New Metric"
    await page.getByRole('button', { name: 'New Metric' }).click();
    
    // 2. Fill form
    await page.getByRole('textbox', { name: 'Name' }).fill('E2E Conviction');
    await page.getByRole('combobox', { name: 'Type' }).selectOption('int');
    await page.getByRole('combobox', { name: 'Scope' }).selectOption('trades');
    await page.getByRole('textbox', { name: 'Description' }).fill('E2E Test Metric');
    
    // Scale labels
    await page.getByRole('spinbutton', { name: 'Minimum' }).fill('1');
    await page.getByRole('spinbutton', { name: 'Maximum' }).fill('10');
    
    // 3. Save
    await page.getByRole('button', { name: 'Save Metric' }).click();
    
    // 4. Verify in list
    await expect(page.locator('table').getByText('E2E Conviction')).toBeVisible();
  });

  test('TC-112 edit an existing metric', async ({ page }) => {
    const row = page.locator('tr', { hasText: 'E2E Conviction' });
    
    // Click the Edit icon
    await row.getByTitle('Edit metric').click();
    
    // Modify
    await page.getByRole('textbox', { name: 'Name' }).fill('E2E Conviction Edited');
    await page.getByRole('button', { name: 'Save Metric' }).click();
    
    // Verify
    await expect(page.locator('table').getByText('E2E Conviction Edited')).toBeVisible();
  });

  test('TC-113 create a new metric (string enum)', async ({ page }) => {
    await page.getByRole('button', { name: 'New Metric' }).click();
    
    await page.getByRole('textbox', { name: 'Name' }).fill('E2E Setup Quality');
    await page.getByRole('combobox', { name: 'Type' }).selectOption('string_enum');
    
    // Option 1 is already there, fill it
    await page.getByPlaceholder('Option 1').fill('A+');
    
    // Add Option 2
    await page.getByRole('button', { name: 'Add option' }).click();
    await page.getByPlaceholder('Option 2').fill('B');
    
    // Save
    await page.getByRole('button', { name: 'Save Metric' }).click();
    
    await expect(page.locator('table').getByText('E2E Setup Quality')).toBeVisible();
  });

  test('TC-114 delete metrics', async ({ page }) => {
    // Delete first metric
    let row = page.locator('tr', { hasText: 'E2E Conviction Edited' });
    await row.getByTitle('Delete metric').click();
    await row.getByRole('button', { name: 'Yes' }).click();
    await expect(row).not.toBeVisible();

    // Delete second metric
    row = page.locator('tr', { hasText: 'E2E Setup Quality' });
    await row.getByTitle('Delete metric').click();
    await row.getByRole('button', { name: 'Yes' }).click();
    await expect(row).not.toBeVisible();
  });
});
