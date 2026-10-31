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
  show_open_trades: false,
  chart_candles_before: 20,
  chart_candles_after: 10,
  chart_show_post_exit: false,
  default_portfolio_id: null,
  home_route: "/dashboard",
  chart_intervals: ["1h", "4h", "1d", "1w"],
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
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
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

  return useMutation<UserSettings, Error, UserSettingsUpdate, { previous: UserSettings | undefined }>({
    mutationFn: async (update: UserSettingsUpdate) => {
      const { data, error } = await updateSettingsApiV1UsersMeSettingsPut({ body: update });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as UserSettings;
    },
    onMutate: async (update) => {
      await qc.cancelQueries({ queryKey: SETTINGS_KEY });
      const previous = qc.getQueryData<UserSettings>(SETTINGS_KEY);
      qc.setQueryData<UserSettings>(SETTINGS_KEY, (old) => {
        const base = old ?? DEFAULT_SETTINGS;
        return {
          ...base,
          ...update,
          features: update.features ?? base.features,
          chart_intervals: update.chart_intervals ?? base.chart_intervals,
        };
      });
      return { previous };
    },
    onError: (_err, _update, context) => {
      if (context?.previous) {
        qc.setQueryData(SETTINGS_KEY, context.previous);
      }
    },
    onSuccess: (data) => {
      qc.setQueryData(SETTINGS_KEY, data);
    },
  });
}
