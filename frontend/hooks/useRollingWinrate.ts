/**
 * React Query hook for rolling win-rate time-series data.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { client } from "@/lib/api/client.gen";
import type { RollingWinratePoint, ResponseEnvelope } from "@/lib/types";

export function useRollingWinrate(windowTrades: number = 20) {
  return useQuery<RollingWinratePoint[], Error>({
    queryKey: ["metrics", "rolling-winrate", windowTrades],
    queryFn: async () => {
      const { data, error } = await client.get<ResponseEnvelope<RollingWinratePoint[]>, unknown, false>({
        url: "/api/v1/timeseries/rolling-winrate",
        query: { window_trades: windowTrades },
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data;
    },
    staleTime: 5 * 60 * 1000,
  });
}
