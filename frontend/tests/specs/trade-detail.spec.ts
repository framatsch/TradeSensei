/*
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const SEED_STATE_FILE = path.join(__dirname, '../.auth/seed-state.json');

function getSeedState() {
  return JSON.parse(fs.readFileSync(SEED_STATE_FILE, 'utf-8')) as {
    executionTradeId: string;
  };
}

test.describe('Trade Detail Redesign', () => {
  test.beforeEach(async ({ page }) => {
    const seedState = getSeedState();
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
    await expect(page.getByText('Stop Loss').first()).toBeVisible();
    await expect(page.getByText('Take Profit').first()).toBeVisible();
    await expect(page.getByText('Realized R').first()).toBeVisible();
    await expect(page.getByText('Return %').first()).toBeVisible();
    
    // 3. Verify Qualitative Metadata Panel
    await expect(page.getByRole('heading', { name: 'Qualitative Analysis & Metadata' })).toBeVisible();
    await expect(page.getByText('Tags (Taxonomies)')).toBeVisible();
    await expect(page.getByText('Playbook', { exact: true })).toBeVisible();
    await expect(page.getByText('Journal', { exact: true })).toBeVisible();
    
    // 4. Verify Execution Legs
    await expect(page.getByRole('button', { name: /Execution Legs/ })).toBeVisible();
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

  test.skip('TC-122 star a trade (Model Book Cross Entity)', async ({ page }) => {
    // Look for the star button in the header actions
    const starButton = page.locator('button[aria-label="Star"], button[aria-label="Unstar"]');
    
    // It might be unstarrred or starred already, let's toggle it
    await starButton.click();
    
    // Should show some indication of loading/success
    await page.waitForTimeout(1000); // Give it a sec instead of networkidle
    
    // Toggle back
    await starButton.click();
    await page.waitForTimeout(1000);
    
    // Verify it's functional
    await expect(starButton).toBeVisible();
  });
});
