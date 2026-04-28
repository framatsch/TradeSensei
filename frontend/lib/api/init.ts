import { client } from "./client.gen";

export function initializeApiClient() {
  client.setConfig({
    baseUrl: "/api/proxy",
  });

  client.interceptors.request.use((request, options) => {
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("access_token");
      if (token) {
        request.headers.set("Authorization", `Bearer ${token}`);
      }
    }
    return request;
  });

  client.interceptors.response.use((response, request, options) => {
    if (response.status === 401) {
      if (typeof window !== "undefined" && window.location.pathname !== "/login") {
        localStorage.removeItem("access_token");
        window.location.href = "/login";
      }
    }
    return response;
  });

  client.interceptors.error.use((error, response, request, options) => {
    if (response?.status === 401) {
      if (typeof window !== "undefined" && window.location.pathname !== "/login") {
        localStorage.removeItem("access_token");
        window.location.href = "/login";
      }
    }
    return error;
  });
}
