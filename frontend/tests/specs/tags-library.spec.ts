import { test, expect } from '@playwright/test';

test.describe('Tags (Taxonomies) Library', () => {
  test.describe.configure({ mode: 'serial' });

  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard/library/tags');
    await page.waitForLoadState('networkidle');
  });

  test('TC-100 navigate to tags page and see the list', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Tags' })).toBeVisible();
    await expect(page.getByText('Manage reusable metadata taxonomies')).toBeVisible();
    
    // The list should be visible
    await expect(page.getByRole('heading', { name: 'Bearish' })).toBeVisible();
  });

  test('TC-101 create a new tag', async ({ page }) => {
    // 1. Click "New Tag"
    await page.getByRole('button', { name: 'New Tag' }).click();
    
    // 2. Fill form
    await page.locator('input[name="name"], input[placeholder="Name"]').or(page.locator('input[type="text"]')).first().fill('E2E Test Tag');
    await page.getByRole('combobox').selectOption('trades');
    await page.getByRole('textbox', { name: 'Tag description' }).fill('A tag created by E2E test');
    
    // Pick a color (second color button)
    const colorButtons = page.locator('button[aria-label^="color #"]');
    await colorButtons.nth(1).click();
    
    // 3. Save
    await page.getByRole('button', { name: 'Save' }).click();
    
    // 4. Verify in list
    await expect(page.getByRole('heading', { name: 'E2E Test Tag' })).toBeVisible();
  });

  test('TC-102 edit an existing tag', async ({ page }) => {
    // Click the Edit icon
    await page.getByRole('button', { name: 'Edit E2E Test Tag' }).click();
    
    // Modify
    await page.locator('input[name="name"], input[placeholder="Name"]').or(page.locator('input[type="text"]')).first().fill('E2E Edited Tag');
    await page.getByRole('button', { name: 'Save' }).click();
    
    // Verify
    await expect(page.getByRole('heading', { name: 'E2E Edited Tag' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'E2E Test Tag' })).not.toBeVisible();
  });

  test('TC-103 delete a tag', async ({ page }) => {
    // Click Delete icon
    await page.getByRole('button', { name: 'Delete E2E Edited Tag' }).click();
    
    // Confirm delete
    await page.getByRole('button', { name: 'Delete', exact: true }).click();
    
    // Verify removal
    await expect(page.getByRole('heading', { name: 'E2E Edited Tag' })).not.toBeVisible();
  });
});
