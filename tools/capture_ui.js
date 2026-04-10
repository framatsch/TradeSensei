const { chromium } = require('playwright');
const path = require('path');

const SCREENSHOT_DIR = path.join(__dirname, '..', 'docs', 'screenshots', 'ui-review');
const BASE_URL = 'http://localhost:3000';
const TRADE_ID = process.argv[2] || '';

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  // Login
  await page.goto(`${BASE_URL}/login`);
  await page.waitForTimeout(2000);
  await page.fill('input[type="text"], input[name="username"], input[placeholder*="user" i], input:first-of-type', 'testuser');
  await page.fill('input[type="password"]', 'Test1234!');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(3000);

  // 1. Trades List page
  await page.goto(`${BASE_URL}/dashboard/trades`);
  await page.waitForTimeout(3000);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '01-trades-list.png'), fullPage: false });
  console.log('Captured: trades list');

  // 2. Trade Detail page (first trade)
  if (TRADE_ID) {
    await page.goto(`${BASE_URL}/dashboard/trades/${TRADE_ID}`);
    await page.waitForTimeout(3000);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '02-trade-detail.png'), fullPage: true });
    console.log('Captured: trade detail');

    // 3. Click Edit Trade
    const editButton = await page.locator('text=Edit Trade').first();
    if (await editButton.isVisible()) {
      await editButton.click();
      await page.waitForTimeout(2000);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, '03-trade-edit-form.png'), fullPage: true });
      console.log('Captured: trade edit form');
    }
  }

  await browser.close();
  console.log('Done! Screenshots saved to:', SCREENSHOT_DIR);
})();
