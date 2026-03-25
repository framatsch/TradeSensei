/**
 * Axios instance with JWT auth interceptor and base URL configuration.
 *
 * The base URL is resolved at runtime from `window.__ENV__.API_URL` (injected
 * by docker-entrypoint.sh via public/env.js) so that a single Docker image can
 * be configured without rebuilding.  Falls back to the build-time env var and
 * then to localhost for local development.
 */

import axios from "axios";

declare global {
  interface Window {
    __ENV__?: { API_URL?: string };
  }
}

function getApiBaseUrl(): string {
  if (typeof window !== "undefined" && window.__ENV__?.API_URL) {
    return window.__ENV__.API_URL;
  }
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
}

const API_BASE_URL = getApiBaseUrl();

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
