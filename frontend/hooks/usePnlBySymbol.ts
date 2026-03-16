/**
 * React Query hook for PnL by symbol time-series data.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import type { PnlBySymbol, ResponseEnvelope } from "@/lib/types";

export function usePnlBySymbol() {
  return useQuery<PnlBySymbol[], Error>({
    queryKey: ["pnl-by-symbol"],
    queryFn: async () => {
      const res = await apiClient.get<ResponseEnvelope<PnlBySymbol[]>>(
        "/api/v1/timeseries/pnl-by-symbol"
      );
      return res.data.data;
    },
    staleTime: 5 * 60 * 1000,
  });
}
