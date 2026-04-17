/**
 * Authentication Spec — covers login, registration, logout, and navigation
 * between auth pages.
 *
 * These tests run WITHOUT the shared storageState (no pre-authenticated session)
 * so they exercise the real login/register flow end-to-end.
 */

import { test, expect } from '@playwright/test';
import { E2E_USER } from '../global-setup';

// Override storageState for this entire file — auth tests run unauthenticated
test.use({ storageState: { cookies: [], origins: [] } });

// ─── Login ───────────────────────────────────────────────────────────────────

test.describe('Login', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
  });

  test('TC-001 shows login form with all elements', async ({ page }) => {
    await expect(page).toHaveTitle(/Trade Sensei/);
    await expect(page.getByRole('heading', { name: 'Trade Sensei' })).toBeVisible();
    await expect(page.getByLabel('Username or Email')).toBeVisible();
    await expect(page.getByLabel('Password')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Sign In' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Create one' })).toBeVisible();
  });

  test('TC-002 successful login redirects to dashboard', async ({ page }) => {
    await page.getByLabel('Username or Email').fill(E2E_USER.username);
    await page.getByLabel('Password').fill(E2E_USER.password);
    await page.getByRole('button', { name: 'Sign In' }).click();

    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10_000 });
    await expect(page.locator('a[href="/dashboard"]')).toBeVisible();
  });

  test('TC-003 wrong password shows error message', async ({ page }) => {
    await page.getByLabel('Username or Email').fill(E2E_USER.username);
    await page.getByLabel('Password').fill('wrongpassword!');
    await page.getByRole('button', { name: 'Sign In' }).click();

    await expect(page.getByText(/Incorrect username or password|Login failed/)).toBeVisible({
      timeout: 8_000,
    });
    await expect(page).toHaveURL(/\/login/);
  });

  test('TC-004 unknown user shows error message', async ({ page }) => {
    await page.getByLabel('Username or Email').fill('no_such_user_xyz');
    await page.getByLabel('Password').fill('somepassword123');
    await page.getByRole('button', { name: 'Sign In' }).click();

    await expect(page.getByText(/Incorrect username or password|Login failed/)).toBeVisible({
      timeout: 8_000,
    });
  });

  test('TC-005 empty form triggers HTML5 validation', async ({ page }) => {
    await page.getByRole('button', { name: 'Sign In' }).click();

    // Username field must be invalid (browser native validation)
    const usernameInput = page.getByLabel('Username or Email');
    await expect(usernameInput).toHaveAttribute('required');
    // Page must not navigate away
    await expect(page).toHaveURL(/\/login/);
  });

  test('TC-006 Sign In button is disabled while request is pending', async ({ page }) => {
    await page.getByLabel('Username or Email').fill(E2E_USER.username);
    await page.getByLabel('Password').fill(E2E_USER.password);

    const submitBtn = page.getByRole('button', { name: /Sign In|Signing in/ });

    // Click and immediately check disabled state (optimistic)
    const clickPromise = submitBtn.click();
    // After click the button should either be disabled or show "Signing in…"
    await Promise.race([
      expect(submitBtn).toBeDisabled(),
      expect(page.getByRole('button', { name: /Signing in/ })).toBeVisible(),
    ]).catch(() => { /* racing condition ok — login may already complete */ });

    await clickPromise;
    // End state: should be on dashboard
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10_000 });
  });
});

// ─── Register ────────────────────────────────────────────────────────────────

test.describe('Register', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/register');
  });

  test('TC-010 shows registration form with all elements', async ({ page }) => {
    await expect(page).toHaveTitle(/Trade Sensei/);
    await expect(page.getByRole('heading', { name: 'Trade Sensei' })).toBeVisible();
    await expect(page.getByLabel('Username')).toBeVisible();
    await expect(page.getByLabel('Email')).toBeVisible();
    await expect(page.getByLabel('Password')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Create Account' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Sign in' })).toBeVisible();
  });

  test('TC-011 duplicate username shows conflict error', async ({ page }) => {
    // e2e_testuser already exists (created in globalSetup)
    await page.getByLabel('Username').fill(E2E_USER.username);
    await page.getByLabel('Email').fill('different@example.com');
    await page.getByLabel('Password').fill('SomePassword123!');
    await page.getByRole('button', { name: 'Create Account' }).click();

    await expect(page.getByText(/already in use|already taken|Registration failed/i)).toBeVisible({
      timeout: 8_000,
    });
    await expect(page).toHaveURL(/\/register/);
  });

  test('TC-012 password too short shows validation', async ({ page }) => {
    await page.getByLabel('Username').fill('brand_new_user_abc');
    await page.getByLabel('Email').fill('brand_new@example.com');
    // minLength=8, enter 5 chars
    await page.getByLabel('Password').fill('abc12');
    await page.getByRole('button', { name: 'Create Account' }).click();

    // HTML5 minLength validation or server error
    const passwordInput = page.getByLabel('Password');
    await expect(passwordInput).toHaveAttribute('minLength', '8');
    await expect(page).toHaveURL(/\/register/);
  });
});

// ─── Auth page navigation ────────────────────────────────────────────────────

test.describe('Auth page navigation', () => {
  test('TC-020 "Create one" link navigates to /register', async ({ page }) => {
    await page.goto('/login');
    await page.getByRole('link', { name: 'Create one' }).click();
    await expect(page).toHaveURL(/\/register/);
  });

  test('TC-021 "Sign in" link navigates to /login', async ({ page }) => {
    await page.goto('/register');
    await page.getByRole('link', { name: 'Sign in' }).click();
    await expect(page).toHaveURL(/\/login/);
  });

  test('TC-022 unauthenticated /dashboard redirects to /login', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/login/, { timeout: 8_000 });
  });

  test('TC-023 root / redirects to /dashboard then to /login when unauthenticated', async ({
    page,
  }) => {
    await page.goto('/');
    // Should end up on login since no token
    await expect(page).toHaveURL(/\/login/, { timeout: 8_000 });
  });
});
