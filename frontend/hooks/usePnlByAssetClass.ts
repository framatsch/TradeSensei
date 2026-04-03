/**
 * React Query hook for PnL by asset class time-series data.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import type { PnlByAssetClass, ResponseEnvelope } from "@/lib/types";

export function usePnlByAssetClass() {
  return useQuery<PnlByAssetClass[], Error>({
    queryKey: ["metrics", "pnl-by-asset-class"],
    queryFn: async () => {
      const res = await apiClient.get<ResponseEnvelope<PnlByAssetClass[]>>(
        "/api/v1/timeseries/pnl-by-asset-class"
      );
      return res.data.data;
    },
    staleTime: 5 * 60 * 1000,
  });
}
