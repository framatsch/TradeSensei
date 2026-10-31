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

import { randomUUID } from 'node:crypto';
import { test as base, expect, type Page } from '@playwright/test';
import { z } from 'zod';

interface SeedTrade {
  id: string;
  symbol: string;
}

interface TradeMobileFixture {
  trades: SeedTrade[];
  createTrade: (symbol: string, exitPrice?: string) => Promise<SeedTrade>;
}

const idEnvelope = z.object({ data: z.object({ id: z.string() }) });
const tokenResponse = z.object({ access_token: z.string() });
const API_URL = process.env.E2E_API_URL ?? 'http://localhost:8000';

export async function expectNoTradeOverflow(page: Page): Promise<void> {
  await expect.poll(() => page.locator('.trade-mobile-contrast').first().evaluate((root) => {
    let scroller = root.parentElement;
    while (scroller && !['auto', 'scroll'].includes(getComputedStyle(scroller).overflowY)) scroller = scroller.parentElement;
    if (!scroller) throw new Error('Trade scroll container not found.');
    return document.documentElement.scrollWidth <= innerWidth + 1 && scroller.scrollWidth <= scroller.clientWidth + 1;
  })).toBe(true);
}

/** Isolated API data: these cases never mutate the shared E2E user's trades. */
export const tradeMobileTest = base.extend<{ tradeMobile: TradeMobileFixture }>({
  tradeMobile: async ({ page, request, baseURL }, runWithFixture) => {
    const username = `e2e_mobile_${randomUUID().replaceAll('-', '').slice(0, 16)}`;
    const password = 'E2eMobileReview123!';
    let token = '';

    async function api(endpoint: string, data?: Record<string, unknown>, method = 'POST'): Promise<unknown> {
      const response = await request.fetch(`${API_URL}/api/v1${endpoint}`, {
        method,
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        data,
      });
      expect(response.ok(), `${method} ${endpoint}: ${await response.text()}`).toBeTruthy();
      if (response.status() === 204) return null;
      const body: unknown = await response.json();
      return body;
    }

    try {
      await api('/auth/register', { username, email: `${username}@example.com`, password });
      const login = await request.post(`${API_URL}/api/v1/auth/token`, { form: { username, password } });
      expect(login.ok(), await login.text()).toBeTruthy();
      token = tokenResponse.parse(await login.json()).access_token;
      const portfolioId = idEnvelope.parse(await api('/portfolios', { name: 'Mobile browser review', base_currency: 'USD' })).data.id;
      const accountId = idEnvelope.parse(await api(`/portfolios/${portfolioId}/accounts`, { name: 'Browser IBKR', type: 'ibkr', currency: 'USD' })).data.id;
      await api('/users/me/settings', {
        show_open_trades: true,
        default_date_range: 'all',
        theme: 'light',
        features: { enable_quick_notes: true },
      }, 'PUT');

      async function createTrade(symbol: string, exitPrice = '186.52'): Promise<SeedTrade> {
        const id = idEnvelope.parse(await api(`/portfolios/${portfolioId}/trades`, {
          account_id: accountId, symbol, direction: 'LONG', asset_class: 'EQUITY',
          quantity: '100', entry_price: '182.40', commission: '1.50',
          stop_loss: '178.00', take_profit: '195.00',
          opened_at: '2026-10-24T09:41:00Z', journal: 'Original journal entry.',
        })).data.id;
        // Session teardown may commit after the create response under parallel load.
        await expect.poll(async () => {
          const visible = await request.get(`${API_URL}/api/v1/portfolios/${portfolioId}/trades/${id}`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          return visible.status();
        }, { intervals: [100, 200, 500], timeout: 5000 }).toBe(200);
        await api(`/portfolios/${portfolioId}/trades/${id}/executions`, {
          direction: 'SHORT', quantity: '100', price: exitPrice, commission: '1.00',
          executed_at: '2026-10-25T15:12:00Z',
        });
        return { id, symbol };
      }

      const trades = [
        await createTrade('AAPL'),
        await createTrade('MSFT', '181.52'),
        await createTrade('TSLA', '183.52'),
      ];
      const appOrigin = new URL(baseURL ?? 'http://localhost:3000').origin;
      await page.addInitScript(({ accessToken, portfolioId, appOrigin }) => {
        if (location.origin !== appOrigin) return;
        localStorage.setItem('access_token', accessToken);
        localStorage.setItem('active_portfolio_id', portfolioId);
        localStorage.setItem('active_app_context', 'portfolio');
        localStorage.setItem('theme', 'light');
      }, { accessToken: token, portfolioId, appOrigin });
      await runWithFixture({ trades, createTrade });
    } finally {
      if (!page.isClosed()) await page.close();
      if (token) {
        const response = await request.delete(`${API_URL}/api/v1/users/me`, { headers: { Authorization: `Bearer ${token}` } });
        expect(response.ok(), 'Could not clean up isolated mobile browser user.').toBeTruthy();
      }
    }
  },
});

export { expect };
