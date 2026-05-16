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
import { googleExchangeApiV1AuthGoogleExchangePost, getMeApiV1UsersMeGet } from "@/lib/api/index";
import type { ResponseEnvelope, User } from "@/lib/types";

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
        const { data: tokenData, error: tokenError } = await googleExchangeApiV1AuthGoogleExchangePost({
          body: { one_time_token: token },
        });
        if (tokenError || !tokenData) {
          router.replace("/login?error=oauth_failed");
          return;
        }
        setToken(tokenData.access_token);

        // Fetch the current user — the JWT interceptor in init.ts provides the header
        const { data: meData, error: meError } = await getMeApiV1UsersMeGet();
        if (meError || !meData) {
          router.replace("/login?error=oauth_failed");
          return;
        }
        setUser((meData as unknown as ResponseEnvelope<User>).data);

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
