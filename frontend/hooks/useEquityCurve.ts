/**
 * React Query hook for the equity curve time series.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import type { EquityCurvePoint, ResponseEnvelope } from "@/lib/types";

export function useEquityCurve() {
  return useQuery<EquityCurvePoint[], Error>({
    queryKey: ["metrics", "equity-curve"],
    queryFn: async () => {
      const res = await apiClient.get<ResponseEnvelope<EquityCurvePoint[]>>(
        "/api/v1/metrics/equity-curve"
      );
      return res.data.data;
    },
    staleTime: 60 * 1000,
  });
}
