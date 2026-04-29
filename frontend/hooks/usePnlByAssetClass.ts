/**
 * React Query hook for PnL by asset class time-series data.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { client } from "@/lib/api/client.gen";
import type { PnlByAssetClass, ResponseEnvelope } from "@/lib/types";

export function usePnlByAssetClass() {
  return useQuery<PnlByAssetClass[], Error>({
    queryKey: ["metrics", "pnl-by-asset-class"],
    queryFn: async () => {
      const { data, error } = await client.get<ResponseEnvelope<PnlByAssetClass[]>, unknown, false>({
        url: "/api/v1/timeseries/pnl-by-asset-class",
      });
      if (error || !data) throw error;
      return data.data;
    },
    staleTime: 5 * 60 * 1000,
  });
}
