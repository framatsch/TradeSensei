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

const ALLOWED_HOME_ROUTES = [
  "/dashboard",
  "/dashboard/trades",
  "/dashboard/library",
  "/dashboard/checkins",
] as const;
type HomeRoute = (typeof ALLOWED_HOME_ROUTES)[number];

export default function RootPage() {
  const router = useRouter();
  const hydrated = useAuthStore((s) => s.hydrated);
  const token = useAuthStore((s) => s.token);
  const hydrate = useAuthStore((s) => s.hydrate);
  const { data: settings, isFetched } = useSettings();

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

    // Wait for settings to load before redirecting
    if (!isFetched) return;

    const home: HomeRoute = ALLOWED_HOME_ROUTES.includes(
      settings?.home_route as HomeRoute,
    )
      ? (settings!.home_route as HomeRoute)
      : "/dashboard";

    router.replace(home);
  }, [hydrated, token, isFetched, settings, router]);

  // Render nothing while waiting
  return null;
}
