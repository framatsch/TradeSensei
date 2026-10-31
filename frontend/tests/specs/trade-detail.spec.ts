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
import { tradeMobileTest, expectNoTradeOverflow as expectNoHorizontalOverflow } from '../fixtures/trade-mobile-layout';

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
    await expect(page.getByRole('heading', { name: 'Performance', exact: true })).toBeVisible();
  });

  test('TC-120 page layout and widgets render correctly', async ({ page }) => {
    // 1. Verify Header
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible(); // Symbol
    await expect(page.getByText('Final P&L')).toBeVisible();
    await expect(page.getByText('Opened:')).toBeVisible();

    // 2. Verify Performance Panel
    const overview = page.locator('#trade-overview-pane');
    const performance = overview.getByRole('heading', { name: 'Performance' }).locator('..');
    await expect(performance).toBeVisible();
    await expect(performance.getByText('Stop Loss', { exact: true })).toBeVisible();
    await expect(performance.getByText('Take Profit', { exact: true })).toBeVisible();
    await expect(performance.getByText('Realized R', { exact: true })).toBeVisible();
    await expect(performance.getByText('Return %', { exact: true })).toBeVisible();

    // 3. Verify Qualitative Metadata Panel
    const journal = page.locator('#trade-journal-pane');
    await expect(journal.getByRole('heading', { name: 'Qualitative Analysis & Metadata' })).toBeVisible();
    await expect(journal.getByText('Tags (Taxonomies)')).toBeVisible();
    await expect(journal.getByText('Playbook', { exact: true })).toBeVisible();
    await expect(journal.getByText('Journal', { exact: true })).toBeVisible();

    // 4. Verify Execution Legs
    await expect(page.getByRole('button', { name: /Execution Legs/ })).toBeVisible();
  });

  test('TC-121 inline edit stop loss and take profit', async ({ page }) => {
    // Edit Stop Loss
    await page.getByTitle('Click to edit Stop Loss').click();
    const slInput = page.getByRole('spinbutton', { name: 'Stop Loss', exact: true });
    await slInput.fill('100.5');
    await slInput.press('Enter');

    // Verify updated value (the button title changes or we can just look for the text)
    await expect(page.getByTitle('Click to edit Stop Loss')).toContainText('$100.50');

    // Edit Take Profit
    await page.getByTitle('Click to edit Take Profit').click();
    const tpInput = page.getByRole('spinbutton', { name: 'Take Profit', exact: true });
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

// spec: openspec/changes/trade-mobile-layout/specs/trade-detail-mobile-ui/spec.md
// Data: isolated live-API fixture; no shared E2E trades are edited.
tradeMobileTest.describe('@trade-mobile-layout detail', () => {
  tradeMobileTest.use({ viewport: { width: 375, height: 812 }, storageState: { cookies: [], origins: [] } });
  tradeMobileTest.setTimeout(60_000);

  tradeMobileTest('mobile tabs preserve an unsaved journal draft without horizontal overflow', async ({ page, tradeMobile }) => {
    // 1. At 375×812 open the seeded execution trade and verify Overview default, hidden inactive panes and no document/main overflow.
    await page.goto(`/dashboard/trades/${tradeMobile.trades[0].id}`);
    await expect(page.getByRole('tab', { name: 'Overview', exact: true })).toHaveAttribute('aria-selected', 'true');
    await expect(page.getByRole('heading', { name: 'Performance', exact: true })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Execution Summary' })).toBeVisible();
    await expect(page.locator('#trade-journal-pane')).toBeHidden();
    await expect(page.locator('#trade-executions-pane')).toBeHidden();
    await expectNoHorizontalOverflow(page);

    // 1b. Maximize chart on mobile and restore it back to normal inline view.
    const maximizeBtn = page.getByRole('button', { name: 'Maximize chart' });
    await expect(maximizeBtn).toBeVisible();
    await maximizeBtn.click();
    const chartDialog = page.getByRole('dialog', { name: 'Maximized trade chart' });
    await expect(chartDialog).toBeVisible();
    await expect(page.getByRole('button', { name: 'Restore chart' })).toBeVisible();
    await page.getByRole('button', { name: 'Restore chart' }).click();
    await expect(chartDialog).toBeHidden();
    await expect(maximizeBtn).toBeVisible();

    // 2. Open Journal, collapse Qualitative Analysis & Metadata to bring Journal up, edit a markdown draft and verify fixed Save/Cancel and the unsaved dot.
    await page.getByRole('tab', { name: /^Journal/ }).click();
    const metadataToggle = page.getByRole('button', { name: 'Qualitative Analysis & Metadata' });
    await expect(metadataToggle).toHaveAttribute('aria-expanded', 'true');
    await metadataToggle.click();
    await expect(metadataToggle).toHaveAttribute('aria-expanded', 'false');
    await expect(page.getByTestId('metadata-collapsed-summary')).toBeVisible();
    await page.getByRole('button', { name: 'Edit journal' }).click();
    const journal = page.getByPlaceholder(/Write your post-trade summary/);
    const draft = '## Mobile review: keep this unsaved draft while switching tabs.';
    await journal.fill(draft);
    await expect(page.getByRole('img', { name: 'Unsaved journal changes' })).toBeVisible();
    const saveBar = page.locator('#trade-journal-pane .fixed');
    await expect(saveBar).toHaveCSS('position', 'fixed');
    await expect(saveBar.getByRole('button', { name: 'Save', exact: true })).toBeVisible();
    await expect(saveBar.getByRole('button', { name: 'Cancel', exact: true })).toBeVisible();
    const barBox = await saveBar.boundingBox();
    if (!barBox) throw new Error('Journal save bar is not rendered.');
    expect(barBox.y + barBox.height).toBeCloseTo(812, 0);
    await expectNoHorizontalOverflow(page);

    // 3. Switch Overview → Executions and verify two active leg cards, the count, hidden table and no overflow.
    await page.getByRole('tab', { name: 'Overview', exact: true }).click();
    await expect(journal).toBeHidden();
    await page.getByRole('tab', { name: 'Executions (2)', exact: true }).click();
    await expect(page.getByTestId('execution-leg-card')).toHaveCount(2);
    await expect(page.getByTestId('execution-leg-card').first()).toBeVisible();
    await expect(page.locator('#executions-table table')).toBeHidden();
    await expectNoHorizontalOverflow(page);

    // 4. Return to Journal, verify exact unsaved draft preserved, then Cancel and verify dirty state clears.
    await page.getByRole('tab', { name: /^Journal/ }).click();
    await expect(journal).toHaveValue(draft);
    await expect(page.getByRole('img', { name: 'Unsaved journal changes' })).toBeVisible();
    await saveBar.getByRole('button', { name: 'Cancel', exact: true }).click();
    await expect(saveBar).toBeHidden();
    await expect(page.getByRole('img', { name: 'Unsaved journal changes' })).toHaveCount(0);

    // 5. At 768×1024, visit every pane and verify no horizontal overflow.
    await page.setViewportSize({ width: 768, height: 1024 });
    for (const name of ['Overview', 'Journal', 'Executions (2)']) {
      await page.getByRole('tab', { name, exact: true }).click();
      await expectNoHorizontalOverflow(page);
    }
  });

  tradeMobileTest('mobile leg card menu edits and persists its price', async ({ page, tradeMobile }) => {
    const trade = tradeMobile.trades[0];
    await page.goto(`/dashboard/trades/${trade.id}`);
    await page.getByRole('tab', { name: 'Executions (2)', exact: true }).click();
    const card = page.getByTestId('execution-leg-card').first();
    await expect(card).toBeVisible();
    await card.getByRole('button', { name: 'Leg actions' }).click();
    for (const name of ['Edit', 'Move to...', 'Detach as new Trade', 'Delete']) {
      await expect(page.getByRole('menuitem', { name, exact: true })).toBeVisible();
    }
    await page.getByRole('menuitem', { name: 'Edit', exact: true }).click();
    const form = card.getByRole('form', { name: 'Edit execution' });
    for (const name of ['Executed at date and time', 'Quantity', 'Price', 'Commission', 'P&L']) {
      await expect(form.getByLabel(name, { exact: true })).toBeVisible();
    }
    await expectNoHorizontalOverflow(page);
    await form.getByLabel('Price', { exact: true }).fill('112.25');
    const update = page.waitForResponse(response => response.request().method() === 'PATCH' && response.url().includes('/executions/'));
    await form.getByRole('button', { name: 'Save', exact: true }).click();
    expect((await update).ok()).toBeTruthy();
    await expect(form).toBeHidden();
    await expect(card).toContainText('100 @ $112.25');
    await page.reload();
    await page.getByRole('tab', { name: 'Executions (2)', exact: true }).click();
    await expect(card).toContainText('100 @ $112.25');
    await expectNoHorizontalOverflow(page);
  });
});
