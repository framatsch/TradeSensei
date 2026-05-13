import { test, expect } from '@playwright/test';

test.describe('Tags (Taxonomies) Library', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard/library/tags');
    await page.waitForLoadState('networkidle');
  });

  test('TC-100 navigate to tags page and see the list', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Tags' })).toBeVisible();
    await expect(page.getByText('Manage reusable metadata taxonomies')).toBeVisible();
    
    // The table should be visible
    await expect(page.locator('table')).toBeVisible();
  });

  test('TC-101 create a new tag', async ({ page }) => {
    // 1. Click "New Tag"
    await page.getByRole('button', { name: 'New Tag' }).click();
    
    // 2. Fill form
    await page.getByRole('textbox', { name: 'Name' }).fill('E2E Test Tag');
    await page.getByRole('combobox', { name: 'Scope' }).selectOption('trades');
    await page.getByRole('textbox', { name: 'Description' }).fill('A tag created by E2E test');
    
    // Pick a color (second color button)
    const colorButtons = page.locator('button[aria-label^="Color #"]');
    await colorButtons.nth(1).click();
    
    // 3. Save
    await page.getByRole('button', { name: 'Save Tag' }).click();
    
    // 4. Verify in list
    await expect(page.locator('table').getByText('E2E Test Tag')).toBeVisible();
  });

  test('TC-102 edit an existing tag', async ({ page }) => {
    const row = page.locator('tr', { hasText: 'E2E Test Tag' });
    
    // Click the Edit icon
    await row.getByTitle('Edit tag').click();
    
    // Modify
    await page.getByRole('textbox', { name: 'Name' }).fill('E2E Edited Tag');
    await page.getByRole('button', { name: 'Save Tag' }).click();
    
    // Verify
    await expect(page.locator('table').getByText('E2E Edited Tag')).toBeVisible();
    await expect(page.locator('table').getByText('E2E Test Tag')).not.toBeVisible();
  });

  test('TC-103 delete a tag', async ({ page }) => {
    const row = page.locator('tr', { hasText: 'E2E Edited Tag' });
    
    // Click Delete icon
    await row.getByTitle('Delete tag').click();
    
    // Confirm delete
    await row.getByRole('button', { name: 'Yes' }).click();
    
    // Verify removal
    await expect(page.locator('table').getByText('E2E Edited Tag')).not.toBeVisible();
  });
});
