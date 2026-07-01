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
 * Root page — redirects to the user's configured home_route (from settings),
 * falling back to /dashboard. If no token is present after hydration, the
 * dashboard layout handles the redirect to /login.
 */

"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";
import { useSettings } from "@/hooks/useSettings";
import { resolveHomeRoute } from "@/lib/homeRoute";

export default function RootPage() {
  const router = useRouter();
  const hydrated = useAuthStore((s) => s.hydrated);
  const token = useAuthStore((s) => s.token);
  const hydrate = useAuthStore((s) => s.hydrate);
  const { data: settings, isFetched, isError } = useSettings();

  // Hydrate token from localStorage on mount
  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (!hydrated) return;

    // No token — let the dashboard layout handle the /login redirect
    if (!token) {
      router.replace("/dashboard");
      return;
    }

    // Wait for settings to resolve (success or error) before redirecting
    if (!isFetched && !isError) return;

    router.replace(resolveHomeRoute(settings?.home_route));
  }, [hydrated, token, isFetched, isError, settings, router]);

  // Render a minimal fallback while waiting so it's not completely blank
  return (
    <div className="flex h-screen w-full items-center justify-center bg-background">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
    </div>
  );
}
