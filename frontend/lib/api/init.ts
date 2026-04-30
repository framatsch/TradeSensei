import { client } from "./client.gen";
import { useAuthStore } from "@/stores/authStore";

let interceptorsRegistered = false;
// Guards against concurrent 401 responses triggering multiple logout+redirect cycles.
// Once set to true it is never reset during the page lifecycle — this is intentional:
// after a 401 the page hard-navigates to /login, so the module is unloaded anyway.
let redirectingToLogin = false;

/**
 * Registers the @hey-api SDK interceptors once at app startup.
 *
 * Note: baseUrl ("/api/proxy") is baked into client.gen.ts via openapi-ts.config.ts
 * and does not need to be set here.
 *
 * - Injects the JWT from localStorage on every request.
 *   Re-reading from localStorage on each request is intentional: the token may be
 *   refreshed between requests, and a closure-cached value would become stale.
 * - Handles 401 Unauthorized responses globally by logging the user out.
 */
export function registerApiInterceptors() {
  if (typeof window === "undefined") return;
  if (interceptorsRegistered) return;
  interceptorsRegistered = true;

  // Inject Authorization header on every outbound request
  client.interceptors.request.use((request, _options) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      request.headers.set("Authorization", `Bearer ${token}`);
    }
    return request;
  });

  // Global 401 handler — log out and redirect on expired or invalid tokens.
  // @hey-api routes all HTTP responses (including 4xx/5xx) through this interceptor.
  client.interceptors.response.use((response, _request, _options) => {
    if (
      response.status === 401 &&
      window.location.pathname !== "/login" &&
      !redirectingToLogin
    ) {
      redirectingToLogin = true;
      // localStorage is cleared by useAuthStore.logout()
      useAuthStore.getState().logout();
      window.location.href = "/login";
    }
    return response;
  });

  // Handles fetch-layer errors (network failure, abort, DNS).
  // Note: @hey-api routes HTTP error responses (4xx/5xx) through the response interceptor
  // above, not here. The error interceptor only fires on genuine JS exceptions where
  // `response` is null/undefined. The 401 check below is a safety net; in practice it is
  // never reached for HTTP 401s.
  client.interceptors.error.use((error, response, _request, _options) => {
    if (
      response?.status === 401 &&
      window.location.pathname !== "/login" &&
      !redirectingToLogin
    ) {
      redirectingToLogin = true;
      useAuthStore.getState().logout();
      window.location.href = "/login";
    }
    return error;
  });
}

/**
 * Resets the interceptor registration state.
 * Exposed for use in tests only — do not call in production code.
 */
export function resetInterceptors() {
  interceptorsRegistered = false;
  redirectingToLogin = false;
}
