/**
 * React Query hook for a single trade by ID.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import type { ResponseEnvelope, Trade } from "@/lib/types";

export function useTrade(id: string) {
  return useQuery<Trade, Error>({
    queryKey: ["trade", id],
    queryFn: async () => {
      const res = await apiClient.get<ResponseEnvelope<Trade>>(
        `/api/v1/trades/${id}`
      );
      return res.data.data;
    },
    staleTime: 30 * 1000,
    enabled: Boolean(id),
  });
}
