import { client } from "./api/client.gen";
import { useAuthStore } from "@/stores/authStore";

let interceptorsRegistered = false;
let redirectingToLogin = false;

/**
 * Registers the @hey-api SDK interceptors once at app startup.
 *
 * - Injects the JWT from localStorage on every request.
 * - Handles 401 Unauthorized responses globally by logging the user out.
 */
export function registerApiInterceptors() {
  if (typeof window === "undefined") return;
  if (interceptorsRegistered) return;
  interceptorsRegistered = true;

  client.setConfig({
    baseUrl: "/api/proxy",
  });

  client.interceptors.request.use((request) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      request.headers.set("Authorization", `Bearer ${token}`);
    }
    return request;
  });

  client.interceptors.response.use((response) => {
    if (
      response.status === 401 &&
      window.location.pathname !== "/login" &&
      !redirectingToLogin
    ) {
      redirectingToLogin = true;
      useAuthStore.getState().logout();
      window.location.href = "/login";
    }
    return response;
  });

  client.interceptors.error.use((error, response) => {
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

export function resetInterceptors() {
  interceptorsRegistered = false;
  redirectingToLogin = false;
}
