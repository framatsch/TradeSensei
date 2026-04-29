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

import { useEffect, useRef, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";
import { Spinner } from "@/components/ui/Spinner";
import type { TokenResponse, ResponseEnvelope, User } from "@/lib/types";
import { client } from "@/lib/api/client.gen";

function OAuthCallbackContent() {
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
        const exchangeRes = await (await client.post({ url: "/api/v1/auth/google/exchange" as any, body: { one_time_token: token } as any })).data as any;
        const accessToken = exchangeRes.data.access_token;
        setToken(accessToken);

        // Fetch the current user to populate the auth store
        const userRes = await (await client.get({ url: "/api/v1/users/me" as any, body: { headers: { Authorization: `Bearer ${accessToken}` } } as any })).data as any;
        setUser(userRes.data.data);

        router.replace("/dashboard");
      } catch {
        router.replace("/login?error=oauth_failed");
      }
    })();
  }, [searchParams, router, setToken, setUser]);

  return (
    <div className="flex flex-col items-center gap-4 text-muted-foreground">
      <Spinner size="lg" />
      <p className="text-sm">Completing sign-in…</p>
    </div>
  );
}

export default function OAuthCallbackPage() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-background">
      <Suspense fallback={
        <div className="flex flex-col items-center gap-4 text-muted-foreground">
          <Spinner size="lg" />
          <p className="text-sm">Loading…</p>
        </div>
      }>
        <OAuthCallbackContent />
      </Suspense>
    </main>
  );
}
