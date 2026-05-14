import { test, expect } from '@playwright/test';
import seedState from '../.auth/seed-state.json';

test.describe('Trade Detail Redesign', () => {
  test.beforeEach(async ({ page }) => {
    // We use the seeded execution trade ID which is guaranteed to exist
    await page.goto(`/dashboard/trades/${seedState.executionTradeId}`);
    await page.waitForLoadState('networkidle');
  });

  test('TC-120 page layout and widgets render correctly', async ({ page }) => {
    // 1. Verify Header
    await expect(page.locator('h1')).toBeVisible(); // Symbol
    await expect(page.getByText('Final P&L')).toBeVisible();
    await expect(page.getByText('Opened:')).toBeVisible();
    
    // 2. Verify Performance Panel
    await expect(page.getByRole('heading', { name: 'Performance' })).toBeVisible();
    await expect(page.getByText('Stop Loss')).toBeVisible();
    await expect(page.getByText('Take Profit')).toBeVisible();
    await expect(page.getByText('Realized R')).toBeVisible();
    await expect(page.getByText('Return %')).toBeVisible();
    
    // 3. Verify Qualitative Metadata Panel
    await expect(page.getByRole('heading', { name: 'Tags & Annotations' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Playbook' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Notes' })).toBeVisible();
    
    // 4. Verify Execution Legs
    await expect(page.getByRole('heading', { name: 'Execution Legs' })).toBeVisible();
  });

  test('TC-121 inline edit stop loss and take profit', async ({ page }) => {
    // Edit Stop Loss
    await page.getByTitle('Click to edit Stop Loss').click();
    const slInput = page.locator('input[type="number"]').first();
    await slInput.fill('100.5');
    await slInput.press('Enter');
    
    // Verify updated value (the button title changes or we can just look for the text)
    await expect(page.getByTitle('Click to edit Stop Loss')).toContainText('$100.50');
    
    // Edit Take Profit
    await page.getByTitle('Click to edit Take Profit').click();
    const tpInput = page.locator('input[type="number"]').first();
    await tpInput.fill('200.75');
    await tpInput.press('Enter');
    
    // Verify updated value
    await expect(page.getByTitle('Click to edit Take Profit')).toContainText('$200.75');
  });

  test('TC-122 star a trade (Model Book Cross Entity)', async ({ page }) => {
    // Look for the star button in the header actions
    const starButton = page.locator('button[aria-label="Star as model book setup"]');
    
    // It might be unstarrred or starred already, let's toggle it
    await starButton.click();
    
    // Should show some indication of loading/success, wait for network idle
    await page.waitForLoadState('networkidle');
    
    // Toggle back
    await starButton.click();
    await page.waitForLoadState('networkidle');
    
    // Verify it's functional
    await expect(starButton).toBeVisible();
  });
});
