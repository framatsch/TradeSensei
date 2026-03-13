/**
 * React Query hook for daily PnL bar chart data (uses metrics summary equity
 * curve as the data source for now since a dedicated endpoint doesn't exist).
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import type { EquityCurvePoint, ResponseEnvelope } from "@/lib/types";

interface DailyPnlBar {
  date: string;
  pnl: number;
}

export function useDailyPnl() {
  return useQuery<DailyPnlBar[], Error>({
    queryKey: ["metrics", "daily-pnl"],
    queryFn: async () => {
      const res = await apiClient.get<ResponseEnvelope<EquityCurvePoint[]>>(
        "/api/v1/metrics/equity-curve"
      );
      // Aggregate per day from individual trade PnL values
      const byDate = new Map<string, number>();
      for (const point of res.data.data) {
        const date = point.timestamp.slice(0, 10);
        byDate.set(date, (byDate.get(date) ?? 0) + parseFloat(point.pnl));
      }
      return Array.from(byDate.entries())
        .map(([date, pnl]) => ({ date, pnl }))
        .sort((a, b) => a.date.localeCompare(b.date));
    },
    staleTime: 60 * 1000,
  });
}
