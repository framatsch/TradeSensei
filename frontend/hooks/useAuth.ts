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
import { resetInterceptors } from "@/lib/apiInterceptors";
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
      // This endpoint does not use ResponseEnvelope, returns AuthConfigResponse directly
      return data as unknown as AuthConfigResponse;
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
      // Reset the redirect-guard so a future 401 after re-login triggers the
      // logout flow again (without this, the flag stays true after session expiry
      // → re-login → next 401 is silently ignored).
      resetInterceptors();
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
