/**
 * React Query hook + mutations for authentication (login, register, logout,
 * current user).
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import {
  getConfigApiV1AuthConfigGet,
  getMeApiV1UsersMeGet,
  loginApiV1AuthTokenPost,
  logoutApiV1AuthLogoutPost,
} from "@/lib/api/index";
import { useAuthStore } from "@/stores/authStore";
import type {
  AuthConfigResponse,
  TokenResponse,
  User,
} from "@/lib/types";

// ─── Auth Config ──────────────────────────────────────────────────────────────

export function useAuthConfig() {
  return useQuery<AuthConfigResponse, Error>({
    queryKey: ["authConfig"],
    queryFn: async () => {
      const { data, error } = await getConfigApiV1AuthConfigGet();
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      // SDK returns ResponseEnvelope; cast to local type
      return (data as unknown as { data: AuthConfigResponse }).data;
    },
    staleTime: 1000 * 60 * 60 * 24, // 24 hours
  });
}

// ─── Current user ─────────────────────────────────────────────────────────────

export function useCurrentUser() {
  const token = useAuthStore((s) => s.token);

  return useQuery<User, Error>({
    queryKey: ["currentUser"],
    queryFn: async () => {
      const { data, error } = await getMeApiV1UsersMeGet();
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return (data as unknown as { data: User }).data;
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
      const { data, error } = await loginApiV1AuthTokenPost({
        body: { username, password, grant_type: "password" },
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data as unknown as TokenResponse;
    },
    onSuccess: async (data) => {
      setToken(data.access_token);
      // Fetch the current user after login — token is now in localStorage via setToken
      const { data: meData, error: meError } = await getMeApiV1UsersMeGet();
      if (!meError && meData) {
        setUser((meData as unknown as { data: User }).data);
      }
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
        await logoutApiV1AuthLogoutPost();
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
