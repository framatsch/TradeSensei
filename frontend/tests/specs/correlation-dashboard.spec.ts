import { test, expect } from '@playwright/test';

test.describe('Metadata Correlation Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to Strategy Analysis (Correlation)
    await page.goto('/dashboard/workspace/performance/strategy');
    await page.waitForLoadState('networkidle');
  });

  test('TC-130 renders scatter widgets for correlation analysis', async ({ page }) => {
    // Both scatter charts should be loaded
    await expect(page.getByRole('heading', { name: /MAE \/ MFE/i })).toBeVisible();
    await expect(page.getByRole('heading', { name: /Duration vs P&L/i })).toBeVisible();
    
    // There shouldn't be an error message
    await expect(page.getByText('Failed to load strategy analysis data.')).not.toBeVisible();
  });
});
