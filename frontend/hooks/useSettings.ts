/**
 * React Query hooks for user UI settings (theme, default_date_range).
 *
 * - useSettings: fetches current user settings
 * - useUpdateSettings: mutation to persist a partial settings update
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import type { ResponseEnvelope, UserSettings, UserSettingsUpdate } from "@/lib/types";

// ─── Query key ────────────────────────────────────────────────────────────────

export const SETTINGS_KEY = ["users", "me", "settings"] as const;

// ─── Defaults (mirrors backend) ───────────────────────────────────────────────

export const DEFAULT_SETTINGS: UserSettings = {
  theme: "system",
  default_date_range: "all",
};

// ─── useSettings ─────────────────────────────────────────────────────────────

/**
 * Fetches the current user's UI settings from the backend.
 * Falls back to DEFAULT_SETTINGS until the query resolves.
 */
export function useSettings() {
  return useQuery<UserSettings, Error>({
    queryKey: SETTINGS_KEY,
    queryFn: async () => {
      const res = await apiClient.get<ResponseEnvelope<UserSettings>>(
        "/api/v1/users/me/settings"
      );
      return res.data.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    placeholderData: DEFAULT_SETTINGS,
  });
}

// ─── useUpdateSettings ────────────────────────────────────────────────────────

/**
 * Persists a partial settings update to the backend.
 * Optimistically updates the cache, rolls back on error.
 */
export function useUpdateSettings() {
  const qc = useQueryClient();

  return useMutation<UserSettings, Error, UserSettingsUpdate>({
    mutationFn: async (update: UserSettingsUpdate) => {
      const res = await apiClient.put<ResponseEnvelope<UserSettings>>(
        "/api/v1/users/me/settings",
        update
      );
      return res.data.data;
    },
    onMutate: async (update) => {
      await qc.cancelQueries({ queryKey: SETTINGS_KEY });
      const previous = qc.getQueryData<UserSettings>(SETTINGS_KEY);
      qc.setQueryData<UserSettings>(SETTINGS_KEY, (old) => ({
        ...(old ?? DEFAULT_SETTINGS),
        ...update,
      }));
      return { previous };
    },
    onError: (_err, _update, context) => {
      const ctx = context as { previous?: UserSettings } | undefined;
      if (ctx?.previous) {
        qc.setQueryData(SETTINGS_KEY, ctx.previous);
      }
    },
    onSuccess: (data) => {
      qc.setQueryData(SETTINGS_KEY, data);
    },
  });
}
