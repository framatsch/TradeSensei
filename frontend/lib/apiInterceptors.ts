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

import { client } from "./api/client.gen";
import { useAuthStore } from "@/stores/authStore";

let interceptorsRegistered = false;
let redirectingToLogin = false;
let isRefreshing = false;
let refreshPromise: Promise<string | null> | null = null;

async function handleUnauthorized(response: Response) {
  if (
    response?.status === 401 &&
    window.location.pathname !== "/login" &&
    !redirectingToLogin
  ) {
    // Verhindere Endlosschleife, falls der Refresh selbst 401 liefert
    if (response.url?.includes("/auth/refresh")) {
      redirectingToLogin = true;
      useAuthStore.getState().logout();
      window.location.href = "/login";
      return;
    }

    if (!isRefreshing) {
      isRefreshing = true;
      refreshPromise = fetch("/api/proxy/api/v1/auth/refresh", { method: "POST" })
        .then(async (res) => {
          if (res.ok) {
            const data = await res.json();
            useAuthStore.getState().setToken(data.access_token);
            return data.access_token;
          }
          return null;
        })
        .catch(() => null)
        .finally(() => {
          isRefreshing = false;
          refreshPromise = null;
        });
    }

    const newToken = await refreshPromise;
    if (!newToken) {
      redirectingToLogin = true;
      useAuthStore.getState().logout();
      window.location.href = "/login";
    }
  }
}

/**
 * Registers the @hey-api SDK interceptors once at app startup.
 *
 * - Injects the JWT from localStorage on every request.
 * - Handles 401 Unauthorized responses globally by attempting silent refresh, then logging the user out if it fails.
 */
export function registerApiInterceptors() {
  if (typeof window === "undefined") return;
  if (interceptorsRegistered) return;
  interceptorsRegistered = true;

  client.setConfig({
    baseUrl: "/api/proxy",
  });

  client.interceptors.request.use(async (request) => {
    // Pausiere neue Requests, während ein Refresh läuft
    if (isRefreshing && refreshPromise) {
      await refreshPromise;
    }

    const token = localStorage.getItem("access_token");
    if (token) {
      request.headers.set("Authorization", `Bearer ${token}`);
    }
    return request;
  });

  client.interceptors.response.use(async (response) => {
    await handleUnauthorized(response);
    return response;
  });

  client.interceptors.error.use(async (error, response) => {
    if (response) {
      await handleUnauthorized(response);
    }
    return error;
  });
}

export function resetInterceptors() {
  interceptorsRegistered = false;
  redirectingToLogin = false;
  isRefreshing = false;
  refreshPromise = null;
}
