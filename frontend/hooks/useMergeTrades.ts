/**
 * React Query hook for merging multiple trades into one.
 */

"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import type { MergeTradesRequest, ResponseEnvelope, Trade } from "@/lib/types";

/** Merge two or more trades into a single surviving trade. */
export function useMergeTrades() {
  const qc = useQueryClient();
  return useMutation<Trade, Error, MergeTradesRequest>({
    mutationFn: async (payload) => {
      const res = await apiClient.post<ResponseEnvelope<Trade>>(
        "/api/v1/trades/merge",
        payload
      );
      return res.data.data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["trades"] });
      void qc.invalidateQueries({ queryKey: ["metrics"] });
    },
  });
}
