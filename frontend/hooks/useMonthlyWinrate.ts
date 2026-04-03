/**
 * React Query hook for monthly win-rate data from GET /timeseries/monthly-winrate.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import type { ResponseEnvelope } from "@/lib/types";

export interface MonthlyWinratePoint {
  year: number;
  month: number;
  label: string;
  win_rate: string;
  win_count: number;
  loss_count: number;
  trade_count: number;
}

export function useMonthlyWinrate(accountId?: string) {
  const params = new URLSearchParams();
  if (accountId) params.set("account_id", accountId);
  const qs = params.toString() ? `?${params.toString()}` : "";

  return useQuery<MonthlyWinratePoint[], Error>({
    queryKey: ["metrics", "monthly-winrate", accountId],
    queryFn: async () => {
      const res = await apiClient.get<ResponseEnvelope<MonthlyWinratePoint[]>>(
        `/api/v1/timeseries/monthly-winrate${qs}`
      );
      return res.data.data;
    },
    staleTime: 5 * 60 * 1000,
  });
}
