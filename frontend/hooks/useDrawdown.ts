/**
 * React Query hook for the drawdown time series.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import type { DrawdownPoint, ResponseEnvelope } from "@/lib/types";

export function useDrawdown() {
  return useQuery<DrawdownPoint[], Error>({
    queryKey: ["metrics", "drawdown"],
    queryFn: async () => {
      const res = await apiClient.get<ResponseEnvelope<DrawdownPoint[]>>(
        "/api/v1/metrics/drawdown"
      );
      return res.data.data;
    },
    staleTime: 60 * 1000,
  });
}
