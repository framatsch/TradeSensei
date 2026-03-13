/**
 * React Query hook + mutations for authentication (login, register, logout,
 * current user).
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import apiClient from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";
import type {
  ResponseEnvelope,
  TokenResponse,
  User,
  UserCreate,
} from "@/lib/types";

// ─── Current user ─────────────────────────────────────────────────────────────

export function useCurrentUser() {
  const token = useAuthStore((s) => s.token);

  return useQuery<User, Error>({
    queryKey: ["currentUser"],
    queryFn: async () => {
      const res = await apiClient.get<ResponseEnvelope<User>>(
        "/api/v1/users/me"
      );
      return res.data.data;
    },
    enabled: !!token,
    staleTime: 5 * 60 * 1000,
  });
}

// ─── Login ────────────────────────────────────────────────────────────────────

interface LoginCredentials {
  username: string;
  password: string;
}

export function useLogin() {
  const setToken = useAuthStore((s) => s.setToken);
  const setUser = useAuthStore((s) => s.setUser);
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation<TokenResponse, Error, LoginCredentials>({
    mutationFn: async ({ username, password }) => {
      const params = new URLSearchParams();
      params.append("username", username);
      params.append("password", password);
      const res = await apiClient.post<TokenResponse>(
        "/api/v1/auth/token",
        params,
        { headers: { "Content-Type": "application/x-www-form-urlencoded" } }
      );
      return res.data;
    },
    onSuccess: async (data) => {
      setToken(data.access_token);
      // Fetch the current user after login
      const userRes = await apiClient.get<ResponseEnvelope<User>>(
        "/api/v1/users/me",
        {
          headers: { Authorization: `Bearer ${data.access_token}` },
        }
      );
      setUser(userRes.data.data);
      await queryClient.invalidateQueries({ queryKey: ["currentUser"] });
      router.push("/dashboard");
    },
  });
}

// ─── Register ─────────────────────────────────────────────────────────────────

export function useRegister() {
  const setToken = useAuthStore((s) => s.setToken);
  const setUser = useAuthStore((s) => s.setUser);
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation<User, Error, UserCreate>({
    mutationFn: async (payload: UserCreate) => {
      const res = await apiClient.post<ResponseEnvelope<User>>(
        "/api/v1/auth/register",
        payload
      );
      return res.data.data;
    },
    onSuccess: async (user) => {
      // Auto-login after registration using the user's credentials
      // We don't have the password here, so the caller must trigger login separately.
      setUser(user);
      await queryClient.invalidateQueries({ queryKey: ["currentUser"] });
      router.push("/dashboard");
    },
  });
}

// ─── Logout ───────────────────────────────────────────────────────────────────

export function useLogout() {
  const logout = useAuthStore((s) => s.logout);
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation<void, Error, void>({
    mutationFn: async () => {
      try {
        await apiClient.post("/api/v1/auth/logout");
      } catch {
        // Even if the backend call fails, clear local state
      }
    },
    onSettled: () => {
      logout();
      queryClient.clear();
      router.push("/login");
    },
  });
}
