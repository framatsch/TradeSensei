/**
 * React Query hook for return distribution histogram data.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import type { ReturnDistribution, ResponseEnvelope } from "@/lib/types";

export function useReturnDistribution() {
  return useQuery<ReturnDistribution[], Error>({
    queryKey: ["return-distribution"],
    queryFn: async () => {
      const res = await apiClient.get<ResponseEnvelope<ReturnDistribution[]>>(
        "/api/v1/timeseries/return-distribution"
      );
      return res.data.data;
    },
    staleTime: 5 * 60 * 1000,
  });
}
