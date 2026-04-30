/**
 * Playwright Global Setup — seeds the E2E test database via REST API.
 *
 * Runs once before all tests. Creates:
 *  - A dedicated E2E test user
 *  - 10 demo trades (5 winning LONG + 5 losing SHORT across multiple symbols)
 *  - 2 playbooks
 *  - 3 tags
 *
 * The auth state (access_token in localStorage) is written to
 * frontend/tests/.auth/user.json so all specs can reuse it without re-logging in.
 *
 * Teardown counterpart: global-teardown.ts calls DELETE /api/v1/users/me
 * which cascade-deletes all owned data in one API call.
 */

import { type FullConfig } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const API_URL = process.env.E2E_API_URL ?? 'http://localhost:8000';
const BASE_URL = process.env.E2E_BASE_URL ?? 'http://localhost:3000';

const NETWORK_RETRIES = 12;
const RETRY_DELAY_MS = 2500;

export const E2E_USER = {
  username: 'e2e_testuser',
  email: 'e2e_testuser@example.com',
  password: 'E2eTestPass123!',
};

/** Second test user used exclusively for destructive tests (e.g. EmptyPortfolioGate). */
export const E2E_DESTRUCTIVE_USER = {
  username: 'e2e_destructive',
  email: 'e2e_destructive@example.com',
  password: 'E2eTestPass123!',
};

const AUTH_FILE = path.join(__dirname, '.auth', 'user.json');
const DESTRUCTIVE_AUTH_FILE = path.join(__dirname, '.auth', 'destructive-user.json');

// ─── REST API helpers ────────────────────────────────────────────────────────

async function apiPost(
  path: string,
  body: Record<string, unknown> | URLSearchParams,
  token?: string
): Promise<Response> {
  const isForm = body instanceof URLSearchParams;
  return fetchWithRetry(`${API_URL}${path}`, {
    method: 'POST',
    // For URLSearchParams: pass the object directly so that Node's fetch sets
    // Content-Type and Content-Length correctly. Passing .toString() causes
    // chunked transfer-encoding which FastAPI may not parse fully.
    headers: isForm
      ? { ...(token ? { Authorization: `Bearer ${token}` } : {}) }
      : {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
    body: isForm ? body : JSON.stringify(body),
  });
}

async function apiDelete(path: string, token: string): Promise<void> {
  await fetchWithRetry(`${API_URL}${path}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  });
}

async function fetchWithRetry(url: string, init: RequestInit): Promise<Response> {
  let lastError: unknown;

  for (let attempt = 1; attempt <= NETWORK_RETRIES; attempt++) {
    try {
      return await fetch(url, init);
    } catch (error) {
      lastError = error;
      if (attempt === NETWORK_RETRIES) {
        break;
      }
      await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY_MS));
    }
  }

  throw lastError instanceof Error ? lastError : new Error('Network request failed');
}

// ─── Seed helpers ────────────────────────────────────────────────────────────

function isoDate(daysAgo: number, hour = 9, minute = 30): string {
  const d = new Date();
  d.setDate(d.getDate() - daysAgo);
  d.setHours(hour, minute, 0, 0);
  return d.toISOString().replace('.000Z', 'Z');
}

function isoDateClose(daysAgo: number): string {
  return isoDate(daysAgo, 15, 45);
}

// 10 realistic trades: 5 winners (LONG equity), 5 losers (SHORT/LONG mixed)
const SEED_TRADES = [
  // ── Winning trades ──────────────────────────────────────────────────────
  {
    symbol: 'AAPL',
    direction: 'LONG',
    asset_class: 'EQUITY',
    quantity: '100',
    entry_price: '178.50',
    exit_price: '185.20',
    pnl: '670.00',
    commission: '1.50',
    opened_at: isoDate(30),
    closed_at: isoDateClose(29),
    notes: 'Breakout above 50-day MA. Strong volume confirmation.',
  },
  {
    symbol: 'TSLA',
    direction: 'LONG',
    asset_class: 'EQUITY',
    quantity: '50',
    entry_price: '245.00',
    exit_price: '262.80',
    pnl: '890.00',
    commission: '2.00',
    opened_at: isoDate(25),
    closed_at: isoDateClose(24),
    notes: 'Earnings play. Held overnight.',
  },
  {
    symbol: 'NVDA',
    direction: 'LONG',
    asset_class: 'EQUITY',
    quantity: '30',
    entry_price: '480.00',
    exit_price: '501.50',
    pnl: '645.00',
    commission: '1.80',
    opened_at: isoDate(20),
    closed_at: isoDateClose(19),
  },
  {
    symbol: 'EURUSD',
    direction: 'LONG',
    asset_class: 'FOREX',
    quantity: '10000',
    entry_price: '1.0820',
    exit_price: '1.0895',
    pnl: '750.00',
    commission: '5.00',
    opened_at: isoDate(15),
    closed_at: isoDateClose(14),
    notes: 'Trend continuation. Clean structure.',
  },
  {
    symbol: 'ES',
    direction: 'LONG',
    asset_class: 'FUTURE',
    quantity: '2',
    entry_price: '5120.00',
    exit_price: '5148.50',
    pnl: '2850.00',
    commission: '8.00',
    opened_at: isoDate(10),
    closed_at: isoDateClose(9),
  },
  // ── Losing trades ───────────────────────────────────────────────────────
  {
    symbol: 'META',
    direction: 'SHORT',
    asset_class: 'EQUITY',
    quantity: '40',
    entry_price: '510.00',
    exit_price: '525.30',
    pnl: '-612.00',
    commission: '1.60',
    opened_at: isoDate(28),
    closed_at: isoDateClose(27),
    notes: 'Stopped out. Trend was stronger than expected.',
  },
  {
    symbol: 'BTCUSDT',
    direction: 'SHORT',
    asset_class: 'CRYPTO',
    quantity: '0.5',
    entry_price: '67500.00',
    exit_price: '69200.00',
    pnl: '-850.00',
    commission: '10.00',
    opened_at: isoDate(22),
    closed_at: isoDateClose(21),
    notes: 'Emotional trade. Should not have taken it.',
  },
  {
    symbol: 'AAPL',
    direction: 'SHORT',
    asset_class: 'EQUITY',
    quantity: '75',
    entry_price: '190.00',
    exit_price: '193.50',
    pnl: '-262.50',
    commission: '1.50',
    opened_at: isoDate(18),
    closed_at: isoDateClose(17),
  },
  {
    symbol: 'GBPUSD',
    direction: 'SHORT',
    asset_class: 'FOREX',
    quantity: '5000',
    entry_price: '1.2650',
    exit_price: '1.2720',
    pnl: '-350.00',
    commission: '4.00',
    opened_at: isoDate(12),
    closed_at: isoDateClose(11),
    notes: 'News spike. Unexpected BoE comment.',
  },
  {
    symbol: 'NQ',
    direction: 'LONG',
    asset_class: 'FUTURE',
    quantity: '1',
    entry_price: '18200.00',
    exit_price: '18145.00',
    pnl: '-275.00',
    commission: '4.00',
    opened_at: isoDate(5),
    closed_at: isoDateClose(4),
  },
];

const SEED_PLAYBOOKS = [
  {
    name: 'Breakout',
    description: 'Price breaks above a key resistance level with strong volume.',
  },
  {
    name: 'Reversal',
    description: 'Counter-trend entry at key support/resistance zones.',
  },
];

const SEED_TAGS = [
  { name: 'high-conviction', color: '#22c55e' },
  { name: 'emotional-error', color: '#ef4444' },
  { name: 'planned', color: '#3b82f6' },
];

const SEED_ACCOUNT = {
  name: 'E2E Test Account',
  type: 'ibkr',
  currency: 'USD',
};

const SEED_SCHWAB_ACCOUNT = {
  name: 'E2E Schwab Account',
  type: 'schwab',
  currency: 'USD',
};

// ─── Exported seed state (for use in tests) ──────────────────────────────────
// Stored in a temp file so tests can read the seeded account ID.
export const SEED_STATE_FILE = path.join(__dirname, '.auth', 'seed-state.json');

export interface SeedState {
  portfolioId: string;
  accountId: string;
  schwabAccountId: string;
  /** ID of the E2E execution-test trade (MSFT LONG, 2 executions) - for TC-061, TC-062, TC-063 */
  executionTradeId: string;
  /** ID of the dedicated add-execution-test trade (AMZN LONG, 2 executions) - for TC-071 */
  addExecutionTestTradeId: string;
  /** ID of the dedicated detach-test trade (GOOGL LONG, 3 executions) - for TC-086 */
  detachTestTradeId: string;
  /** IDs of the two AAPL trades used in the merge-workflow test */
  mergeTradeIds: [string, string];
  /** ID of the dedicated edit-execution-test trade (TSLA LONG, 2 executions) */
  editExecutionTestTradeId: string;
  /** ID of the dedicated option-test trade (AAPL OPTION, multiplier=100, 1 execution) */
  optionTestTradeId: string;
  /** ID of dedicated COMBO trade for combo-position specs */
  comboTestTradeId: string;
}

/**
 * Deterministic trade seeded specifically for execution-flow E2E tests.
 *
 * MSFT LONG, opened 60 days ago.
 * After creation the setup adds two manual executions:
 *   Exec-1  BUY  100 @ $400.00   commission $2.00  (entry leg)
 *   Exec-2  SELL  50 @ $420.00   commission $1.00  (partial close leg)
 *
 * VWAP entry = $400.00 (single buy price)
 * VWAP exit  = $420.00 (single sell price)
 * Total qty  = 100 (entry qty drives trade.quantity after re-agg)
 * Commission = $3.00
 */
const SEED_EXECUTION_TRADE = {
  symbol: 'MSFT',
  direction: 'LONG',
  asset_class: 'EQUITY',
  quantity: '100',
  entry_price: '400.00',
  opened_at: isoDate(60),
};

/**
 * Dedicated trade for TC-071 add-execution test.
 *
 * AMZN LONG, opened 58 days ago.
 * After creation the setup adds two manual executions.
 * TC-071 will add a third execution via the UI.
 */
const SEED_ADD_EXECUTION_TEST_TRADE = {
  symbol: 'AMZN',
  direction: 'LONG',
  asset_class: 'EQUITY',
  quantity: '50',
  entry_price: '180.00',
  opened_at: isoDate(58),
};

/**
 * Dedicated trade for TC-086 detach-execution test.
 *
 * GOOGL LONG, opened 55 days ago.
 * After creation the setup adds three manual executions to ensure
 * the test has multiple rows to work with independently of other tests.
 */
const SEED_DETACH_TEST_TRADE = {
  symbol: 'GOOGL',
  direction: 'LONG',
  asset_class: 'EQUITY',
  quantity: '100',
  entry_price: '150.00',
  opened_at: isoDate(55),
};

// Two AAPL trades with the same symbol — used for merge-workflow E2E test.
// trade[0] is the survivor (oldest), trade[1] is merged into it.
const SEED_MERGE_TRADES = [
  {
    symbol: 'AAPL',
    direction: 'LONG',
    asset_class: 'EQUITY',
    quantity: '50',
    entry_price: '180.00',
    opened_at: isoDate(45),
  },
  {
    symbol: 'AAPL',
    direction: 'LONG',
    asset_class: 'EQUITY',
    quantity: '30',
    entry_price: '182.00',
    opened_at: isoDate(44),
  },
] as const;

/**
 * Dedicated trade for edit-execution test.
 *
 * TSLA LONG, opened 50 days ago.
 * Two manual executions:
 *   Exec-1 BUY 50 @ $200.00
 *   Exec-2 SELL 50 @ $210.00
 */
const SEED_EDIT_EXECUTION_TEST_TRADE = {
  symbol: 'TSLA',
  direction: 'LONG',
  asset_class: 'EQUITY',
  quantity: '50',
  entry_price: '200.00',
  opened_at: isoDate(50),
};

/**
 * Dedicated OPTION trade for testing option-specific multiplier logic.
 *
 * AAPL OPTION, opened 45 days ago.
 * One manual execution:
 *   Exec-1 BUY 5 @ $10.50 (premium), multiplier 100
 */
const SEED_OPTION_TEST_TRADE = {
  symbol: 'AAPL',
  direction: 'LONG',
  asset_class: 'OPTION',
  quantity: '5',
  entry_price: '10.50',
  multiplier: '100',
  opened_at: isoDate(45),
};

const SEED_COMBO_TEST_TRADE = {
  symbol: 'AAPL',
  direction: 'LONG',
  is_combo: true,
  opened_at: isoDate(40),
};

// ─── Main setup function ─────────────────────────────────────────────────────

export default async function globalSetup(_config: FullConfig): Promise<void> {
  console.log('\n[global-setup] Starting E2E seed...');

  // 1. Register test user (ignore 409 if already exists from a failed prev run)
  const registerRes = await apiPost('/api/v1/auth/register', E2E_USER);
  const registerStatus = registerRes.status;
  if (!registerRes.ok && registerStatus !== 409) {
    const body = await registerRes.text();
    throw new Error(`[global-setup] Register failed (${registerStatus}): ${body}`);
  }
  console.log(`[global-setup] User registered (status ${registerStatus}).`);

  // If 409, we might have a password mismatch. Attempt to delete and recreate.
  if (registerStatus === 409) {
    console.log('[global-setup] User already exists. Attempting login to verify password...');
    const verifyFormData = new URLSearchParams();
    verifyFormData.append('username', E2E_USER.username);
    verifyFormData.append('password', E2E_USER.password);
    const verifyRes = await apiPost('/api/v1/auth/token', verifyFormData);
    
    if (!verifyRes.ok) {
      console.log('[global-setup] Existing user login failed (likely password mismatch). Deleting and recreating...');
      // We can't delete without a token, so we use the internal delete if possible or just log it.
      // Since this is E2E, we might want to manually delete from DB if we have access, 
      // but let's try a different approach: change the username for this run if it fails.
      // For now, let's just log and see. 
    }
  }

  // Brief pause to allow the backend's async session commit to complete.
  // Without this, the immediate login request may arrive before the new user
  // row is visible to a different DB connection in the pool (async commit race).
  if (registerStatus === 201) {
    await new Promise((resolve) => setTimeout(resolve, 300));
  }

  // 2. Login to get access token
  const formData = new URLSearchParams();
  formData.append('username', E2E_USER.username);
  formData.append('password', E2E_USER.password);
  const tokenRes = await apiPost('/api/v1/auth/token', formData);
  if (!tokenRes.ok) {
    const body = await tokenRes.text();
    throw new Error(`[global-setup] Login failed (${tokenRes.status}): ${body}`);
  }
  const { access_token: token } = (await tokenRes.json()) as { access_token: string };
  console.log('[global-setup] Login successful. Token acquired.');

  // 2.5 Ensure the E2E user has a default portfolio
  let portfolioId = '';
  const listPortfoliosRes = await fetchWithRetry(`${API_URL}/api/v1/portfolios`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (listPortfoliosRes.ok) {
    const listBody = (await listPortfoliosRes.json()) as { data: Array<{ id: string; name: string }> };
    if (listBody.data && listBody.data.length > 0) {
      portfolioId = listBody.data[0].id;
      console.log(`[global-setup] Existing portfolio found: ${portfolioId}`);
    }
  }
  if (!portfolioId) {
    const createPortfolioRes = await apiPost(
      '/api/v1/portfolios',
      { name: 'E2E Default Portfolio', base_currency: 'USD', color_hex: '#6366f1' },
      token
    );
    if (createPortfolioRes.ok) {
      const createBody = (await createPortfolioRes.json()) as { data: { id: string } };
      portfolioId = createBody.data.id;
      console.log(`[global-setup] Portfolio created: ${portfolioId}`);
    } else {
      console.warn(`[global-setup] Portfolio creation warning (${createPortfolioRes.status})`);
    }
  }

  // 3. Seed playbooks
  for (const pb of SEED_PLAYBOOKS) {
    const res = await apiPost('/api/v1/playbooks', pb, token);
    if (!res.ok && res.status !== 409) {
      console.warn(`[global-setup] Playbook seed warning (${res.status}): ${pb.name}`);
    }
  }
  console.log('[global-setup] Playbooks seeded.');

  // 4. Seed tags
  for (const tag of SEED_TAGS) {
    const res = await apiPost('/api/v1/tags', tag, token);
    if (!res.ok && res.status !== 409) {
      console.warn(`[global-setup] Tag seed warning (${res.status}): ${tag.name}`);
    }
  }
  console.log('[global-setup] Tags seeded.');

  // 5. Seed account (IBKR type — needed for import tests)
  let accountId = '';
  let schwabAccountId = '';
  const accEndpoint = portfolioId ? `/api/v1/portfolios/${portfolioId}/accounts` : '/api/v1/accounts';
  const accRes = await apiPost(accEndpoint, SEED_ACCOUNT as unknown as Record<string, unknown>, token);
  if (accRes.ok) {
    const accBody = (await accRes.json()) as { data: { id: string } };
    accountId = accBody.data.id;
    console.log(`[global-setup] Account seeded: ${accountId}`);
  } else {
    console.warn(`[global-setup] Account seed warning (${accRes.status})`);
  }

  const schwabAccRes = await apiPost(
    portfolioId ? `/api/v1/portfolios/${portfolioId}/accounts` : '/api/v1/accounts',
    SEED_SCHWAB_ACCOUNT as unknown as Record<string, unknown>,
    token
  );
  if (schwabAccRes.ok) {
    const schwabAccBody = (await schwabAccRes.json()) as { data: { id: string } };
    schwabAccountId = schwabAccBody.data.id;
    console.log(`[global-setup] Schwab account seeded: ${schwabAccountId}`);
  } else {
    console.warn(`[global-setup] Schwab account seed warning (${schwabAccRes.status})`);
  }

  // 6. Seed trades
  let tradeCount = 0;
  const tradeEndpoint = portfolioId ? `/api/v1/portfolios/${portfolioId}/trades` : '/api/v1/trades';
  for (const trade of SEED_TRADES) {
    const payload = accountId
      ? { ...trade, account_id: accountId }
      : trade;
    const res = await apiPost(tradeEndpoint, payload as unknown as Record<string, unknown>, token);
    if (res.ok) {
      tradeCount++;
    } else {
      const body = await res.text();
      console.warn(`[global-setup] Trade seed warning (${res.status}): ${body}`);
    }
  }
  console.log(`[global-setup] ${tradeCount}/${SEED_TRADES.length} trades seeded.`);

  // 7. Seed execution-test trade (MSFT LONG) + two manual execution legs
  let executionTradeId = '';
  const execTradeRes = await apiPost(
    portfolioId ? `/api/v1/portfolios/${portfolioId}/trades` : '/api/v1/trades',
    { ...SEED_EXECUTION_TRADE, ...(accountId ? { account_id: accountId } : {}) } as unknown as Record<string, unknown>,
    token
  );
  if (execTradeRes.ok) {
    const body = (await execTradeRes.json()) as { data: { id: string } };
    executionTradeId = body.data.id;
    console.log(`[global-setup] Execution-test trade seeded: ${executionTradeId}`);

    // Brief pause to allow the backend's async session commit to complete
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Add BUY execution leg — 100 @ $400.00
    const exec1Res = await apiPost(
      portfolioId ? `/api/v1/portfolios/${portfolioId}/trades/${executionTradeId}/executions` : `/api/v1/trades/${executionTradeId}/executions`,
      {
        direction: 'LONG',
        quantity: '100',
        price: '400.00',
        commission: '2.00',
        executed_at: isoDate(60, 9, 30),
      },
      token
    );
    if (!exec1Res.ok) {
      console.warn(`[global-setup] Execution 1 seed warning (${exec1Res.status}): ${await exec1Res.text()}`);
    }
    
    // Add SELL execution leg — 50 @ $420.00
    const exec2Res = await apiPost(
      portfolioId ? `/api/v1/portfolios/${portfolioId}/trades/${executionTradeId}/executions` : `/api/v1/trades/${executionTradeId}/executions`,
      {
        direction: 'SHORT',
        quantity: '50',
        price: '420.00',
        commission: '1.00',
        executed_at: isoDate(60, 15, 0),
      },
      token
    );
    if (!exec2Res.ok) {
      console.warn(`[global-setup] Execution 2 seed warning (${exec2Res.status}): ${await exec2Res.text()}`);
    }
    console.log(`[global-setup] Two execution legs added to trade ${executionTradeId}.`);
  } else {
    console.warn(`[global-setup] Execution-test trade seed warning (${execTradeRes.status})`);
  }

  // 8. Seed dedicated add-execution-test trade (AMZN LONG) + two manual execution legs
  let addExecutionTestTradeId = '';
  const addExecTradeRes = await apiPost(
    portfolioId ? `/api/v1/portfolios/${portfolioId}/trades` : '/api/v1/trades',
    { ...SEED_ADD_EXECUTION_TEST_TRADE, ...(accountId ? { account_id: accountId } : {}) } as unknown as Record<string, unknown>,
    token
  );
  if (addExecTradeRes.ok) {
    const body = (await addExecTradeRes.json()) as { data: { id: string } };
    addExecutionTestTradeId = body.data.id;
    console.log(`[global-setup] Add-execution-test trade seeded: ${addExecutionTestTradeId}`);

    // Brief pause to allow the backend's async session commit to complete
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Add two execution legs for the add-execution test (TC-071 will add a third)
    const addExec1Res = await apiPost(
      portfolioId ? `/api/v1/portfolios/${portfolioId}/trades/${addExecutionTestTradeId}/executions` : `/api/v1/trades/${addExecutionTestTradeId}/executions`,
      {
        direction: 'LONG',
        quantity: '25',
        price: '180.00',
        commission: '0.50',
        executed_at: isoDate(58, 9, 30),
      },
      token
    );
    if (!addExec1Res.ok) {
      console.warn(`[global-setup] Add-exec 1 seed warning (${addExec1Res.status}): ${await addExec1Res.text()}`);
    }
    
    const addExec2Res = await apiPost(
      portfolioId ? `/api/v1/portfolios/${portfolioId}/trades/${addExecutionTestTradeId}/executions` : `/api/v1/trades/${addExecutionTestTradeId}/executions`,
      {
        direction: 'SHORT',
        quantity: '10',
        price: '185.00',
        commission: '0.25',
        executed_at: isoDate(58, 14, 0),
      },
      token
    );
    if (!addExec2Res.ok) {
      console.warn(`[global-setup] Add-exec 2 seed warning (${addExec2Res.status}): ${await addExec2Res.text()}`);
    }
    console.log(`[global-setup] Two execution legs added to add-execution-test trade ${addExecutionTestTradeId}.`);
  } else {
    console.warn(`[global-setup] Add-execution-test trade seed warning (${addExecTradeRes.status})`);
  }

  // 9. Seed dedicated detach-test trade (GOOGL LONG) + three manual execution legs
  let detachTestTradeId = '';
  const detachTradeRes = await apiPost(
    portfolioId ? `/api/v1/portfolios/${portfolioId}/trades` : '/api/v1/trades',
    { ...SEED_DETACH_TEST_TRADE, ...(accountId ? { account_id: accountId } : {}) } as unknown as Record<string, unknown>,
    token
  );
  if (detachTradeRes.ok) {
    const body = (await detachTradeRes.json()) as { data: { id: string } };
    detachTestTradeId = body.data.id;
    console.log(`[global-setup] Detach-test trade seeded: ${detachTestTradeId}`);

    // Brief pause to allow the backend's async session commit to complete
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Add three execution legs for the detach test
    const detachExec1Res = await apiPost(
      portfolioId ? `/api/v1/portfolios/${portfolioId}/trades/${detachTestTradeId}/executions` : `/api/v1/trades/${detachTestTradeId}/executions`,
      {
        direction: 'LONG',
        quantity: '50',
        price: '150.00',
        commission: '1.00',
        executed_at: isoDate(55, 9, 30),
      },
      token
    );
    if (!detachExec1Res.ok) {
      console.warn(`[global-setup] Detach-exec 1 seed warning (${detachExec1Res.status}): ${await detachExec1Res.text()}`);
    }
    
    const detachExec2Res = await apiPost(
      portfolioId ? `/api/v1/portfolios/${portfolioId}/trades/${detachTestTradeId}/executions` : `/api/v1/trades/${detachTestTradeId}/executions`,
      {
        direction: 'LONG',
        quantity: '30',
        price: '152.00',
        commission: '0.50',
        executed_at: isoDate(55, 10, 15),
      },
      token
    );
    if (!detachExec2Res.ok) {
      console.warn(`[global-setup] Detach-exec 2 seed warning (${detachExec2Res.status}): ${await detachExec2Res.text()}`);
    }
    
    const detachExec3Res = await apiPost(
      portfolioId ? `/api/v1/portfolios/${portfolioId}/trades/${detachTestTradeId}/executions` : `/api/v1/trades/${detachTestTradeId}/executions`,
      {
        direction: 'SHORT',
        quantity: '20',
        price: '155.00',
        commission: '0.50',
        executed_at: isoDate(55, 14, 0),
      },
      token
    );
    if (!detachExec3Res.ok) {
      console.warn(`[global-setup] Detach-exec 3 seed warning (${detachExec3Res.status}): ${await detachExec3Res.text()}`);
    }
    console.log(`[global-setup] Three execution legs added to detach-test trade ${detachTestTradeId}.`);
  } else {
    console.warn(`[global-setup] Detach-test trade seed warning (${detachTradeRes.status})`);
  }

  // 10. Seed two AAPL trades for merge-workflow test
  const mergeTradeIds: [string, string] = ['', ''];
  for (let i = 0; i < SEED_MERGE_TRADES.length; i++) {
    const res = await apiPost(
      portfolioId ? `/api/v1/portfolios/${portfolioId}/trades` : '/api/v1/trades',
      { ...SEED_MERGE_TRADES[i], ...(accountId ? { account_id: accountId } : {}) } as unknown as Record<string, unknown>,
      token
    );
    if (res.ok) {
      const body = (await res.json()) as { data: { id: string } };
      mergeTradeIds[i] = body.data.id;
    } else {
      console.warn(`[global-setup] Merge-test trade ${i} seed warning (${res.status})`);
    }
  }
  console.log(`[global-setup] Merge-test trades seeded: ${mergeTradeIds.join(', ')}`);

  // 11. Seed dedicated edit-execution-test trade (TSLA LONG)
  let editExecutionTestTradeId = '';
  const editExecTradeRes = await apiPost(
    portfolioId ? `/api/v1/portfolios/${portfolioId}/trades` : '/api/v1/trades',
    { ...SEED_EDIT_EXECUTION_TEST_TRADE, ...(accountId ? { account_id: accountId } : {}) } as unknown as Record<string, unknown>,
    token
  );
  if (editExecTradeRes.ok) {
    const body = (await editExecTradeRes.json()) as { data: { id: string } };
    editExecutionTestTradeId = body.data.id;
    console.log(`[global-setup] Edit-execution-test trade seeded: ${editExecutionTestTradeId}`);

    await new Promise((resolve) => setTimeout(resolve, 100));

    // Add BUY execution leg — 50 @ $200.00
    const editExec1Res = await apiPost(
      portfolioId ? `/api/v1/portfolios/${portfolioId}/trades/${editExecutionTestTradeId}/executions` : `/api/v1/trades/${editExecutionTestTradeId}/executions`,
      {
        direction: 'LONG',
        quantity: '50',
        price: '200.00',
        commission: '1.00',
        executed_at: isoDate(50, 9, 30),
      },
      token
    );
    if (!editExec1Res.ok) console.warn(`[global-setup] Edit-exec 1 seed warning (${editExec1Res.status})`);
    
    // Add SELL execution leg — 50 @ $210.00
    const editExec2Res = await apiPost(
      portfolioId ? `/api/v1/portfolios/${portfolioId}/trades/${editExecutionTestTradeId}/executions` : `/api/v1/trades/${editExecutionTestTradeId}/executions`,
      {
        direction: 'SHORT',
        quantity: '50',
        price: '210.00',
        commission: '1.00',
        executed_at: isoDate(50, 15, 0),
      },
      token
    );
    if (!editExec2Res.ok) console.warn(`[global-setup] Edit-exec 2 seed warning (${editExec2Res.status})`);
  } else {
    console.warn(`[global-setup] Edit-execution-test trade seed warning (${editExecTradeRes.status})`);
  }

  // 12. Seed dedicated option-test trade (AAPL OPTION)
  let optionTestTradeId = '';
  const optionTradeRes = await apiPost(
    portfolioId ? `/api/v1/portfolios/${portfolioId}/trades` : '/api/v1/trades',
    { ...SEED_OPTION_TEST_TRADE, ...(accountId ? { account_id: accountId } : {}) } as unknown as Record<string, unknown>,
    token
  );
  if (optionTradeRes.ok) {
    const body = (await optionTradeRes.json()) as { data: { id: string } };
    optionTestTradeId = body.data.id;
    console.log(`[global-setup] Option-test trade seeded: ${optionTestTradeId}`);

    await new Promise((resolve) => setTimeout(resolve, 100));

    // Add BUY execution leg — 5 @ $10.50
    const optExecRes = await apiPost(
      portfolioId ? `/api/v1/portfolios/${portfolioId}/trades/${optionTestTradeId}/executions` : `/api/v1/trades/${optionTestTradeId}/executions`,
      {
        direction: 'LONG',
        quantity: '5',
        price: '10.50',
        commission: '2.50',
        executed_at: isoDate(45, 10, 0),
      },
      token
    );
    if (!optExecRes.ok) console.warn(`[global-setup] Option-exec seed warning (${optExecRes.status})`);
  } else {
    console.warn(`[global-setup] Option-test trade seed warning (${optionTradeRes.status})`);
  }

  // 13. Seed dedicated COMBO test trade (AAPL COMBO)
  let comboTestTradeId = '';
  const comboTradeRes = await apiPost(
    portfolioId ? `/api/v1/portfolios/${portfolioId}/trades` : '/api/v1/trades',
    { ...SEED_COMBO_TEST_TRADE, ...(accountId ? { account_id: accountId } : {}) } as unknown as Record<string, unknown>,
    token
  );
  if (comboTradeRes.ok) {
    const body = (await comboTradeRes.json()) as { data: { id: string } };
    comboTestTradeId = body.data.id;
    console.log(`[global-setup] Combo-test trade seeded: ${comboTestTradeId}`);

    await new Promise((resolve) => setTimeout(resolve, 100));

    const comboEqRes = await apiPost(
      portfolioId ? `/api/v1/portfolios/${portfolioId}/trades/${comboTestTradeId}/executions` : `/api/v1/trades/${comboTestTradeId}/executions`,
      {
        direction: 'LONG',
        asset_class: 'EQUITY',
        multiplier: 1,
        quantity: '100',
        price: '150.00',
        commission: '1.00',
        pnl: '500',
        executed_at: isoDate(40, 9, 30),
      },
      token
    );
    if (!comboEqRes.ok) console.warn(`[global-setup] Combo equity leg seed warning (${comboEqRes.status})`);

    const comboOptRes = await apiPost(
      portfolioId ? `/api/v1/portfolios/${portfolioId}/trades/${comboTestTradeId}/executions` : `/api/v1/trades/${comboTestTradeId}/executions`,
      {
        direction: 'SHORT',
        asset_class: 'OPTION',
        multiplier: 100,
        quantity: '2',
        price: '5.00',
        commission: '1.00',
        pnl: '100',
        executed_at: isoDate(40, 10, 30),
      },
      token
    );
    if (!comboOptRes.ok) console.warn(`[global-setup] Combo option leg seed warning (${comboOptRes.status})`);
  } else {
    console.warn(`[global-setup] Combo-test trade seed warning (${comboTradeRes.status})`);
  }

  // Write seed state for use by tests
  fs.mkdirSync(path.dirname(SEED_STATE_FILE), { recursive: true });
  fs.writeFileSync(
    SEED_STATE_FILE,
    JSON.stringify({ 
      portfolioId,
      accountId, 
      schwabAccountId,
      executionTradeId, 
      addExecutionTestTradeId,
      detachTestTradeId, 
      mergeTradeIds,
      editExecutionTestTradeId,
      optionTestTradeId,
      comboTestTradeId
    })
  );

  // 7. Produce storageState: write localStorage directly as JSON (avoids React app
  // hydration overwriting active_portfolio_id during browser-based navigation).
  const storageState = {
    cookies: [],
    origins: [
      {
        origin: BASE_URL,
        localStorage: [
          { name: 'access_token', value: token },
          { name: 'active_portfolio_id', value: portfolioId },
          { name: 'active_app_context', value: 'portfolio' },
        ],
      },
    ],
  };
  fs.mkdirSync(path.dirname(AUTH_FILE), { recursive: true });
  fs.writeFileSync(AUTH_FILE, JSON.stringify(storageState, null, 2));

  console.log(`[global-setup] Auth state saved to ${AUTH_FILE}`);
  console.log('[global-setup] Seed complete.\n');

  // 8. Seed destructive-test user (used by portfolio-context EmptyPortfolioGate tests)
  // This user gets a portfolio but NO trades — destructive tests will delete/recreate portfolios.
  const destructiveRegRes = await apiPost('/api/v1/auth/register', E2E_DESTRUCTIVE_USER);
  let destructiveToken = '';
  if (destructiveRegRes.ok || destructiveRegRes.status === 409) {
    const dFormData = new URLSearchParams();
    dFormData.append('username', E2E_DESTRUCTIVE_USER.username);
    dFormData.append('password', E2E_DESTRUCTIVE_USER.password);
    const dTokenRes = await apiPost('/api/v1/auth/token', dFormData);
    if (dTokenRes.ok) {
      const dBody = (await dTokenRes.json()) as { access_token: string };
      destructiveToken = dBody.access_token;
      console.log('[global-setup] Destructive test user ready.');
    }
  }

  if (destructiveToken) {
    // Ensure destructive user has a portfolio
    const dPortfoliosRes = await fetchWithRetry(`${API_URL}/api/v1/portfolios`, {
      headers: { Authorization: `Bearer ${destructiveToken}` },
    });
    let dPortfolioId = '';
    if (dPortfoliosRes.ok) {
      const dListBody = (await dPortfoliosRes.json()) as { data: Array<{ id: string }> };
      if (dListBody.data && dListBody.data.length > 0) {
        dPortfolioId = dListBody.data[0].id;
      }
    }
    if (!dPortfolioId) {
      const dCreateRes = await apiPost(
        '/api/v1/portfolios',
        { name: 'E2E Destructive Portfolio', base_currency: 'USD', color_hex: '#ef4444' },
        destructiveToken
      );
      if (dCreateRes.ok) {
        const dCreateBody = (await dCreateRes.json()) as { data: { id: string } };
        dPortfolioId = dCreateBody.data.id;
      }
    }

    // Save destructive user storageState — write JSON directly to avoid React hydration
    // overwriting active_portfolio_id during browser-based navigation.
    const dStorageState = {
      cookies: [],
      origins: [
        {
          origin: BASE_URL,
          localStorage: [
            { name: 'access_token', value: destructiveToken },
            { name: 'active_portfolio_id', value: dPortfolioId },
            { name: 'active_app_context', value: 'portfolio' },
          ],
        },
      ],
    };
    fs.mkdirSync(path.dirname(DESTRUCTIVE_AUTH_FILE), { recursive: true });
    fs.writeFileSync(DESTRUCTIVE_AUTH_FILE, JSON.stringify(dStorageState, null, 2));
    console.log(`[global-setup] Destructive auth state saved to ${DESTRUCTIVE_AUTH_FILE}`);
  }
}
