/**
 * React Query hook for monthly PnL time-series data.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import type { MonthlyPnl, ResponseEnvelope } from "@/lib/types";

export function useMonthlyPnl() {
  return useQuery<MonthlyPnl[], Error>({
    queryKey: ["metrics", "monthly-pnl"],
    queryFn: async () => {
      const res = await apiClient.get<ResponseEnvelope<MonthlyPnl[]>>(
        "/api/v1/timeseries/monthly-pnl"
      );
      return res.data.data;
    },
    staleTime: 5 * 60 * 1000,
  });
}
