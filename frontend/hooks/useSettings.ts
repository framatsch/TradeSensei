/**
 * React Query hooks for user UI settings (theme, default_date_range).
 *
 * - useSettings: fetches current user settings
 * - useUpdateSettings: mutation to persist a partial settings update
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getSettingsApiV1UsersMeSettingsGet,
  updateSettingsApiV1UsersMeSettingsPut,
} from "@/lib/api/index";
import type { UserSettings, UserSettingsUpdate } from "@/lib/types";

// ─── Query key ────────────────────────────────────────────────────────────────

export const SETTINGS_KEY = ["users", "me", "settings"] as const;

// ─── Defaults (mirrors backend) ───────────────────────────────────────────────

export const DEFAULT_SETTINGS: UserSettings = {
  theme: "system",
  default_date_range: "all",
  features: {},
  chart_candles_before: 20,
  chart_candles_after: 10,
  chart_show_post_exit: false,
  default_portfolio_id: null,
  home_route: "/dashboard",
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
      const { data, error } = await getSettingsApiV1UsersMeSettingsGet();
      if (error || !data) throw error;
      return data.data as UserSettings;
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
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data, error } = await updateSettingsApiV1UsersMeSettingsPut({ body: update as any });
      if (error || !data) throw error;
      return data.data as UserSettings;
    },
    onMutate: async (update) => {
      await qc.cancelQueries({ queryKey: SETTINGS_KEY });
      const previous = qc.getQueryData<UserSettings>(SETTINGS_KEY);
      qc.setQueryData<UserSettings>(SETTINGS_KEY, (old) => {
        const base = (old ?? DEFAULT_SETTINGS) as UserSettings;
        return {
          ...base,
          ...(update as Partial<UserSettings>),
          features: (update as any)?.features ?? base.features,
        } as UserSettings;
      });
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
