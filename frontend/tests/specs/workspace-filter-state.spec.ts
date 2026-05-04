import { test, expect } from '@playwright/test';

test.describe('Workspace Filter State', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard/workspace/reporting');
    await page.waitForLoadState('networkidle');
  });

  test('filter state persists across workspace routes', async ({ page }) => {
    // Try to find the filter toggle and open it
    const filterToggle = page.locator('button:has-text("Filters")').first();
    if (await filterToggle.isVisible()) {
      await filterToggle.click();
      await page.waitForTimeout(500);
    }

    // Set a date filter
    const dateInput = page.locator('input[type="date"]').first();
    if (await dateInput.isVisible()) {
      await dateInput.fill('2024-01-01');
      await dateInput.press('Enter');
      
      // Wait for debounce and URL update
      await page.waitForTimeout(600);
      await expect(page).toHaveURL(/date_from=2024-01-01/);

      // Navigate to another workspace route
      await page.getByRole('link', { name: 'Strategy' }).first().click();
      
      // Verify URL search params are preserved
      await expect(page).toHaveURL(/date_from=2024-01-01/);
      
      // Verify filter value is still active in the UI
      if (await filterToggle.isVisible()) {
        await filterToggle.click();
        await page.waitForTimeout(500);
      }
      await expect(page.locator('input[type="date"]').first()).toHaveValue('2024-01-01');
    }
  });
});
