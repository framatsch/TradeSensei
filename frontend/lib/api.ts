/**
 * Axios instance with JWT auth interceptor.
 *
 * All browser-side API calls go through the Next.js reverse proxy at
 * `/api/proxy/v1/...` — the backend is never contacted directly from the
 * browser.  This keeps the backend off the public internet.
 *
 * The proxy handler (`app/api/proxy/[...path]/route.ts`) forwards requests to
 * `INTERNAL_API_URL` (set via environment variable at container start).
 *
 * For local development without the proxy (e.g. running `next dev` standalone)
 * set NEXT_PUBLIC_API_URL=http://localhost:8000 and the client will call the
 * backend directly.
 */

import axios from "axios";

/**
 * In production the browser calls the Next.js proxy (relative URL).
 * In local dev without Docker, fall back to the backend URL directly.
 */
const API_BASE_URL =
  process.env.NODE_ENV === "production"
    ? "/api/proxy"
    : (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000");

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Attach JWT from localStorage on every request
apiClient.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Handle 401 Unauthorized errors globally
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      if (typeof window !== "undefined" && window.location.pathname !== "/login") {
        localStorage.removeItem("access_token");
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;
