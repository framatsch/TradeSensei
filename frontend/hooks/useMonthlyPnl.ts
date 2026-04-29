/**
 * React Query hook for monthly PnL time-series data.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { client } from "@/lib/api/client.gen";
import type { MonthlyPnl, ResponseEnvelope } from "@/lib/types";

export function useMonthlyPnl() {
  return useQuery<MonthlyPnl[], Error>({
    queryKey: ["metrics", "monthly-pnl"],
    queryFn: async () => {
      const { data, error } = await client.get<ResponseEnvelope<MonthlyPnl[]>, unknown, false>({
        url: "/api/v1/timeseries/monthly-pnl",
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data;
    },
    staleTime: 5 * 60 * 1000,
  });
}
