/**
 * React Query hook for PnL by symbol time-series data.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { client } from "@/lib/api/client.gen";
import type { PnlBySymbol, ResponseEnvelope } from "@/lib/types";

export function usePnlBySymbol() {
  return useQuery<PnlBySymbol[], Error>({
    queryKey: ["metrics", "pnl-by-symbol"],
    queryFn: async () => {
      const { data, error } = await client.get<ResponseEnvelope<PnlBySymbol[]>, unknown, false>({
        url: "/api/v1/timeseries/pnl-by-symbol",
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data;
    },
    staleTime: 5 * 60 * 1000,
  });
}
