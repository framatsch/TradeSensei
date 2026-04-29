import { client } from "./client.gen";

/**
 * Configures the @hey-api generated SDK client once at app startup.
 *
 * - Routes all requests through the Next.js reverse proxy at /api/proxy
 *   (keeps the backend off the public internet)
 * - Injects the JWT from localStorage on every request
 * - Handles 401 Unauthorized responses globally by logging the user out
 */
export function initializeApiClient() {
  // Task 1.2: Set base URL to the Next.js proxy
  client.setConfig({
    baseUrl: "/api/proxy",
  });

  // Task 1.3: Inject Authorization header on every request
  client.interceptors.request.use((request, _options) => {
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("access_token");
      if (token) {
        request.headers.set("Authorization", `Bearer ${token}`);
      }
    }
    return request;
  });

  // Task 1.4: Global 401 handler — log out and redirect to /login
  client.interceptors.response.use((response, _request, _options) => {
    if (
      response.status === 401 &&
      typeof window !== "undefined" &&
      window.location.pathname !== "/login"
    ) {
      localStorage.removeItem("access_token");
      window.location.href = "/login";
    }
    return response;
  });
}
