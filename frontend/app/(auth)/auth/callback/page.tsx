/**
 * OAuth callback page — exchanges the one-time token from the URL query
 * string for a full JWT access token and stores it in the auth store.
 *
 * Flow:
 *   1. Backend redirects here: /auth/callback?token=<one_time_token>
 *   2. This page POSTs the token to POST /api/v1/auth/google/exchange
 *   3. On success: stores access token, fetches current user, goes to /dashboard
 *   4. On error: redirects to /login?error=<code>
 */

"use client";

import { useEffect, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import apiClient from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";
import { Spinner } from "@/components/ui/Spinner";
import type { TokenResponse, ResponseEnvelope, User } from "@/lib/types";

export default function OAuthCallbackPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const setToken = useAuthStore((s) => s.setToken);
  const setUser = useAuthStore((s) => s.setUser);
  const didRun = useRef(false);

  useEffect(() => {
    // Strict-mode guard — only run once
    if (didRun.current) return;
    didRun.current = true;

    const token = searchParams.get("token");
    const error = searchParams.get("error");

    if (error || !token) {
      const code = error ?? "oauth_failed";
      router.replace(`/login?error=${encodeURIComponent(code)}`);
      return;
    }

    (async () => {
      try {
        // Exchange the one-time token for a full access token
        const exchangeRes = await apiClient.post<TokenResponse>(
          "/api/v1/auth/google/exchange",
          { one_time_token: token }
        );
        const accessToken = exchangeRes.data.access_token;
        setToken(accessToken);

        // Fetch the current user to populate the auth store
        const userRes = await apiClient.get<ResponseEnvelope<User>>(
          "/api/v1/users/me",
          { headers: { Authorization: `Bearer ${accessToken}` } }
        );
        setUser(userRes.data.data);

        router.replace("/dashboard");
      } catch {
        router.replace("/login?error=oauth_failed");
      }
    })();
  }, [searchParams, router, setToken, setUser]);

  return (
    <main className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900">
      <div className="flex flex-col items-center gap-4 text-slate-600 dark:text-slate-400">
        <Spinner size="lg" />
        <p className="text-sm">Completing sign-in…</p>
      </div>
    </main>
  );
}
